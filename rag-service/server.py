"""Async gRPC server entry point for RAG service."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated"))

import grpc
from loguru import logger

from config.model_config import load_config


async def serve():
    config = load_config()

    from generated import kb_management_pb2_grpc
    from generated import document_pb2_grpc
    from generated import search_pb2_grpc
    from generated import chat_pb2_grpc

    from kb_service import faiss_service  # noqa: F401
    from services.kb_management_service import KBManagementServicer
    from services.document_service import DocumentServicer
    from services.search_service import SearchServicer
    from services.chat import ChatServicer

    server = grpc.aio.server(
        options=[
            ("grpc.max_send_message_length", 100 * 1024 * 1024),
            ("grpc.max_receive_message_length", 100 * 1024 * 1024),
        ],
    )

    kb_management_pb2_grpc.add_KBManagementServiceServicer_to_server(
        KBManagementServicer(config), server
    )
    document_pb2_grpc.add_DocumentServiceServicer_to_server(
        DocumentServicer(config), server
    )
    search_pb2_grpc.add_SearchServiceServicer_to_server(
        SearchServicer(config), server
    )
    chat_pb2_grpc.add_ChatServiceServicer_to_server(
        ChatServicer(config), server
    )

    server.add_insecure_port("0.0.0.0:50051")
    logger.info("Async RAG gRPC server starting on port 50051")
    await server.start()
    logger.info("All services registered. Waiting for requests...")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
