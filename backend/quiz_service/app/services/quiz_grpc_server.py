import grpc
from app.services.grpc_generated import quiz_service_pb2, quiz_service_pb2_grpc
from app.services.quiz_service import QuizService
from app.repositories.quiz_repository import QuizRepository
from app.db.mongo_client import mongo_db
from opentelemetry import trace
from opentelemetry.context import attach, detach
from opentelemetry.propagate import extract
from my_observability import get_logger

logger = get_logger(__name__)

class QuizServiceServicer(quiz_service_pb2_grpc.QuizServiceServicer):
    def __init__(self, quiz_service: QuizService):
        self.quiz_service = quiz_service

    async def GetQuizById(self, request, context):
        tracer = trace.get_tracer(__name__)
        # Extract W3C trace context from gRPC metadata so this server span
        # becomes a child of the incoming HTTP/gRPC distributed trace.
        metadata = {item.key: item.value for item in context.invocation_metadata()}
        extracted_ctx = extract(metadata)
        token = attach(extracted_ctx)
        try:
            with tracer.start_as_current_span("grpc.GetQuizById"):
                quiz_data = self.quiz_service.get_quiz_by_id(request.quizId)

                if not quiz_data:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "Quiz not found")

                return quiz_service_pb2.Quiz(
                    quizId=quiz_data["quizId"],
                    title=quiz_data.get("title", ""),
                    questions=[
                        quiz_service_pb2.Question(
                            id=q["id"],
                            question_text=q["question_text"],
                            options=q["options"],
                            correct_option=q["correct_option"]
                        )
                        for q in quiz_data.get("questions", [])
                    ]
                )
        finally:
            detach(token)

async def serve():
    repo = QuizRepository(mongo_db.quizzes)
    service = QuizService(repo)

    server = grpc.aio.server()
    quiz_service_pb2_grpc.add_QuizServiceServicer_to_server(
        QuizServiceServicer(quiz_service=service), server
    )
    server.add_insecure_port("[::]:50051")
    await server.start()
    logger.info("Quiz gRPC server running on port 50051")
    await server.wait_for_termination()