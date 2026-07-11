import json
from fastapi import status
from app.schemas.generation import QuizGenerateRequest, QuizGenerateResponse
from app.prompts.prompt_manager import PromptManager
from typing import Dict
from pydantic import ValidationError
from app.exception import AIProviderError
from ollama import AsyncClient, ResponseError, RequestError
from my_observability import get_logger

logger = get_logger(__name__)

class QuizGeneratorService:
    def __init__(self, ollama_client: AsyncClient, model_name: str, prompt_manager: PromptManager):
        self.ollama_client = ollama_client
        self.model_name = model_name
        self.prompt_manager = prompt_manager

    def _build_message(self, request: QuizGenerateRequest) -> list[Dict[str, str]]:
        prompt_template = self.prompt_manager.get("quiz_generator")

        system_content = prompt_template.system_prompt
        user_content = prompt_template.user_template.format(topic=request.topic, count=request.num_questions, difficulty=request.difficulty, language=request.language)

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    async def generate_quiz_preview(self, request: QuizGenerateRequest) -> QuizGenerateResponse:
        """
        Sends a generation request to Ollama, parses the internal JSON text,
        and validates it against the Pydantic response schema.
        """
        messages = self._build_message(request)

        try:
            response = await self.ollama_client.chat(
                model=self.model_name,
                messages=messages,
                options={"temperature": 0.7},
                stream=False,
                format=QuizGenerateResponse.model_json_schema()
            )

            raw_ai_text = response["message"]["content"]
            return QuizGenerateResponse.model_validate_json(raw_ai_text)

        except ResponseError as exc:
            logger.error(f"Ollama API returned error {exc.status_code}. Detail: {exc.error}")
            raise AIProviderError(
                status_code=status.HTTP_502_BAD_GATEWAY,
                title="AI Provider Failure",
                detail="The upstream AI engine failed to process the request."
            )
        except RequestError as exc:
            logger.error(f"Connection to Ollama failed or timed out: {str(exc)}")
            raise AIProviderError(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                title="AI Provider Timeout",
                detail="The AI generation server took too long to respond or is unreachable."
            )
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            logger.warning(f"LLM generated unparseable structured format: {str(exc)}")
            raise AIProviderError(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                title="AI Validation Error",
                detail="The AI generated data that did not match required structural integrity rules."
            )