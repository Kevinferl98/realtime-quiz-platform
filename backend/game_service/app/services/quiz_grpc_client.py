import grpc
import os
from app.services.grpc_generated import quiz_service_pb2, quiz_service_pb2_grpc
from opentelemetry.propagate import inject
from typing import Optional, Dict
from app.exception import QuizNotFoundError
from my_observability import get_logger

QUIZ_SERVICE_HOST = os.getenv("QUIZ_SERVICE_HOST", "quiz_service:50051")
GRPC_TIMEOUT_SECONDS = float(os.getenv("GRPC_TIMEOUT_SECONDS", "5.0"))

logger = get_logger(__name__)

class QuizServiceClient:
    def __init__(self, host: str = QUIZ_SERVICE_HOST):
        self.host = host
        # Long-lived channels to avoid connection overhead per request
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[quiz_service_pb2_grpc.QuizServiceStub] = None

    async def start(self) -> None:
        """Initialize the long-lived gRPC channel and stub during app startup."""
        if not self._channel:
            options = [
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 10000),
                ('grpc.keepalive_permit_without_calls', 1),
                ('grpc.http2.max_pings_without_data', 0)
            ]
            self._channel = grpc.aio.insecure_channel(self.host, options=options)
            self._stub = quiz_service_pb2_grpc.QuizServiceStub(self._channel)
            logger.info(f"gRPC Channel connected to {self.host}")

    async def close(self) -> None:
        """Gracefully close the gRPC channel during app shutdown."""
        if self._channel:
            await self._channel.close(grace=2.0)
            self._channel = None
            self._stub = None
            logger.info("gRPC Channel closed")

    def _build_trace_metadata(self) -> list:
        """Inject OpenTelemetry context into gRPC metadata for distributed tracing."""
        carrier: Dict[str, str] = {}
        inject(carrier)
        return list(carrier.items())

    async def get_quiz_by_id(self, quiz_id: str):
        if not self._stub:
            raise RuntimeError("QuizServiceClient is not initialized.")

        try:
            response = await self._stub.GetQuizById(
                quiz_service_pb2.GetQuizRequest(quizId=quiz_id),
                metadata=self._build_trace_metadata(),
                timeout=GRPC_TIMEOUT_SECONDS
            )

            return {
                "quizId": response.quizId,
                "title": response.title,
                "questions": [
                    {
                        "id": q.id,
                        "question_text": q.question_text,
                        "options": list(q.options),
                        "correct_option": q.correct_option,
                    }
                    for q in response.questions
                ]
            }
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise QuizNotFoundError()
            if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logger.error(f"gRPC timeout fetching quiz {quiz_id}")
                raise
            logger.error(f"gRPC error ({e.code()}): {e.details()}")
            raise