"""gRPC KBManagementService implementation."""
import json
import re
from pathlib import Path
from datetime import datetime

import grpc
from loguru import logger

from config.model_config import AppConfig
from kb_service.kb_service import KBServiceFactory

_KB_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9一-鿿_-]{1,64}$')

from generated import kb_management_pb2
from generated import kb_management_pb2_grpc
from generated import common_pb2


class KBManagementServicer(kb_management_pb2_grpc.KBManagementServiceServicer):
    """Manages knowledge base lifecycle: create, list, delete, update, stats."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.persist_dir = Path(config.vector_store.persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.persist_dir / "_kb_registry.json"
        self._registry: dict = self._load_registry()
        logger.info(f"KBManagementServicer initialized, persist_dir={self.persist_dir}")

    def _load_registry(self) -> dict:
        if self._registry_path.exists():
            try:
                with open(self._registry_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_registry(self):
        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(self._registry, f, ensure_ascii=False, indent=2)

    def CreateKB(self, request, context):
        """Create a new knowledge base by initialising an empty FAISS index."""
        try:
            name = request.name
            description = request.description
            vs_type_str = common_pb2.KBType.Name(request.vs_type).lower() if request.vs_type else "faiss"

            if not name:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("KB name is required")
                return kb_management_pb2.KBInfo()

            if not _KB_NAME_PATTERN.match(name):
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("KB name must be 1-64 chars: alphanumeric, Chinese, underscore, hyphen")
                return kb_management_pb2.KBInfo()

            # Check for duplicate name
            for kb_id_str, entry in self._registry.items():
                if entry["name"] == name:
                    context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                    context.set_details(f"KB with name '{name}' already exists")
                    return kb_management_pb2.KBInfo()

            # Initialise the vector store
            kb_service = KBServiceFactory.get_service(
                kb_name=name,
                vs_type=vs_type_str,
                persist_dir=str(self.persist_dir),
            )
            kb_service.save()

            # Store in registry
            now = datetime.now().isoformat()
            kb_id = len(self._registry) + 1
            self._registry[str(kb_id)] = {
                "id": kb_id,
                "name": name,
                "description": description,
                "vs_type": vs_type_str,
                "embed_model": common_pb2.EmbedModel.Name(request.embed_model),
                "created_at": now,
                "updated_at": now,
            }
            self._save_registry()

            logger.info(f"KB created: id={kb_id}, name={name}, type={vs_type_str}")

            return kb_management_pb2.KBInfo(
                id=kb_id,
                name=name,
                description=description,
                vs_type=request.vs_type,
                embed_model=request.embed_model,
                file_count=0,
                chunk_count=0,
                created_at=now,
                updated_at=now,
            )

        except Exception as e:
            logger.error(f"CreateKB failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return kb_management_pb2.KBInfo()

    def ListKBs(self, request, context):
        """List all knowledge bases with optional pagination."""
        try:
            page = request.page.page if request.page and request.page.page > 0 else 1
            page_size = request.page.page_size if request.page and request.page.page_size > 0 else 20

            kb_list = []
            for kb_id_str, entry in self._registry.items():
                kb_id = entry["id"]
                kb_name = entry["name"]
                # Get stats from the actual FAISS service
                try:
                    kb_svc = KBServiceFactory.get_service(
                        kb_name=kb_name,
                        vs_type=entry["vs_type"],
                        persist_dir=str(self.persist_dir),
                    )
                    chunk_count = kb_svc.get_document_count()
                except Exception:
                    chunk_count = 0

                vs_type_val = common_pb2.KBType.Value(entry["vs_type"].upper()) if entry["vs_type"].upper() in common_pb2.KBType.keys() else common_pb2.FAISS
                embed_model_val = common_pb2.EmbedModel.Value(entry.get("embed_model", "TEXT_EMBEDDING_3_SMALL"))

                kb_list.append(kb_management_pb2.KBInfo(
                    id=kb_id,
                    name=kb_name,
                    description=entry.get("description", ""),
                    vs_type=vs_type_val,
                    embed_model=embed_model_val,
                    file_count=0,
                    chunk_count=chunk_count,
                    created_at=entry.get("created_at", ""),
                    updated_at=entry.get("updated_at", ""),
                ))

            total = len(kb_list)
            start = (page - 1) * page_size
            end = start + page_size
            kb_list = kb_list[start:end]

            page_info = common_pb2.PageInfo(
                total=total,
                page=page,
                page_size=page_size,
            )

            return kb_management_pb2.ListKBResponse(kb_list=kb_list, page=page_info)

        except Exception as e:
            logger.error(f"ListKBs failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return kb_management_pb2.ListKBResponse()

    def DeleteKB(self, request, context):
        """Delete a knowledge base and all its vector data."""
        try:
            kb_id_str = str(request.kb_id)
            entry = self._registry.pop(kb_id_str, None)

            if entry is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"KB with id={request.kb_id} not found")
                return common_pb2.StatusResponse(success=False, message="KB not found")

            kb_name = entry["name"]
            try:
                kb_svc = KBServiceFactory.get_service(
                    kb_name=kb_name,
                    vs_type=entry["vs_type"],
                    persist_dir=str(self.persist_dir),
                )
                kb_svc.clear()
            except Exception as ex:
                logger.warning(f"Error clearing KB data for {kb_name}: {ex}")

            self._save_registry()
            logger.info(f"KB deleted: id={request.kb_id}, name={kb_name}")

            return common_pb2.StatusResponse(
                success=True,
                message=f"KB '{kb_name}' deleted successfully",
            )

        except Exception as e:
            logger.error(f"DeleteKB failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.StatusResponse(success=False, message=str(e))

    def UpdateKB(self, request, context):
        """Update KB name or description."""
        try:
            kb_id_str = str(request.kb_id)
            entry = self._registry.get(kb_id_str)

            if entry is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"KB with id={request.kb_id} not found")
                return kb_management_pb2.KBInfo()

            old_name = entry["name"]
            if request.name:
                entry["name"] = request.name
            if request.description:
                entry["description"] = request.description

            entry["updated_at"] = datetime.now().isoformat()

            # Rename FAISS files if name changed
            if request.name and request.name != old_name:
                old_index = self.persist_dir / f"{old_name}.faiss"
                old_pkl = self.persist_dir / f"{old_name}.pkl"
                new_index = self.persist_dir / f"{request.name}.faiss"
                new_pkl = self.persist_dir / f"{request.name}.pkl"
                if old_index.exists():
                    old_index.rename(new_index)
                if old_pkl.exists():
                    old_pkl.rename(new_pkl)

            self._save_registry()

            vs_type_val = common_pb2.KBType.Value(entry["vs_type"].upper()) if entry["vs_type"].upper() in common_pb2.KBType.keys() else common_pb2.FAISS
            embed_model_val = common_pb2.EmbedModel.Value(entry.get("embed_model", "TEXT_EMBEDDING_3_SMALL"))

            logger.info(f"KB updated: id={request.kb_id}, old_name={old_name}, new_name={entry['name']}")

            return kb_management_pb2.KBInfo(
                id=entry["id"],
                name=entry["name"],
                description=entry.get("description", ""),
                vs_type=vs_type_val,
                embed_model=embed_model_val,
                file_count=0,
                chunk_count=0,
                created_at=entry.get("created_at", ""),
                updated_at=entry.get("updated_at", ""),
            )

        except Exception as e:
            logger.error(f"UpdateKB failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return kb_management_pb2.KBInfo()

    def GetKBStats(self, request, context):
        """Get statistics for a knowledge base."""
        try:
            kb_id_str = str(request.kb_id)
            entry = self._registry.get(kb_id_str)

            if entry is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"KB with id={request.kb_id} not found")
                return kb_management_pb2.KBStatsResponse()

            kb_name = entry["name"]
            try:
                kb_svc = KBServiceFactory.get_service(
                    kb_name=kb_name,
                    vs_type=entry["vs_type"],
                    persist_dir=str(self.persist_dir),
                )
                chunk_count = kb_svc.get_document_count()
                all_texts = kb_svc.get_all_texts()

                # Count file extensions from metadata
                ext_distribution: dict[str, int] = {}
                for doc in all_texts:
                    ext = doc.get("metadata", {}).get("source_ext", "unknown")
                    ext_distribution[ext] = ext_distribution.get(ext, 0) + 1

                file_count = len(set(
                    doc.get("metadata", {}).get("source_file", "")
                    for doc in all_texts
                ))
            except Exception:
                chunk_count = 0
                file_count = 0
                ext_distribution = {}

            return kb_management_pb2.KBStatsResponse(
                kb_id=request.kb_id,
                file_count=file_count,
                chunk_count=chunk_count,
                total_file_size=0,
                file_ext_distribution=ext_distribution,
            )

        except Exception as e:
            logger.error(f"GetKBStats failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return kb_management_pb2.KBStatsResponse()
