import os
import yaml
from pydantic import BaseModel, ValidationError
from app.exception import PromptNotFoundError
from my_observability import get_logger

class PromptTemplate(BaseModel):
    system_prompt: str
    user_template: str

logger = get_logger(__name__)

class PromptManager:
    def __init__(self, registry_path: str | None = None) -> None:
        self._registry: dict[str, PromptTemplate] = {}
        self.registry_path = registry_path or os.path.join(
            os.path.dirname(__file__), "registry"
        )

    def load_prompts(self) -> None:
        if not os.path.exists(self.registry_path):
            logger.error(f"Prompt registry directory not found at: {self.registry_path}")
            raise FileNotFoundError("Registry path does not exist.")

        for filename in os.listdir(self.registry_path):
            if filename.endswith((".yaml", ".yml")):
                name = os.path.splitext(filename)[0]
                full_path = os.path.join(self.registry_path, filename)

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)

                    if not data:
                        logger.warning(f"Skipping empty prompt file: {filename}")
                        continue

                    self._registry[name] = PromptTemplate(
                        system_prompt=data["system_prompt"],
                        user_template=data["user_template"],
                    )
                    logger.info(f"Successfully loaded prompt template: '{name}'")

                except (yaml.YAMLError, KeyError, ValidationError) as exc:
                    logger.critical(f"Failed to parse prompt file {filename}: {exc}")
                    raise RuntimeError(f"Malformed prompt file {filename}") from exc

    def get(self, name: str) -> PromptTemplate:
        if name not in self._registry:
            logger.error(f"Prompt template '{name}' requested but not found.")
            raise PromptNotFoundError()
        return self._registry[name]