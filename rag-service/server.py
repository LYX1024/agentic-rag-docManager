"""gRPC server entry point for RAG service."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated"))

import grpc
from concurrent import futures
from loguru import logger

from config.model_config import load_config


def serve():
    config = load_config()

    # Lazy imports so config is loaded first
    from generated import kb_management_pb2_grpc
    from generated import document_pb2_grpc
    from generated import search_pb2_grpc
    from generated import chat_pb2_grpc

    from services.kb_management_service import KBManagementServicer
    from services.document_service import DocumentServicer
    from services.search_service import SearchServicer
    from services.chat_service import ChatServicer

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
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

    server.add_insecure_port("[::]:50051")
    logger.info("RAG gRPC server starting on port 50051")
    server.start()
    logger.info("All services registered. Waiting for requests...")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
