import yaml
import pytest
from pydantic import ValidationError
from unittest.mock import mock_open, patch
from app.exception import PromptNotFoundError
from app.prompts.prompt_manager import PromptManager, PromptTemplate

@pytest.fixture
def valid_yaml_str():
    return """
    system_prompt: "You are a helpful assistant."
    user_template: "Answer this question: {question}"
    """

@patch("app.prompts.prompt_manager.os.path.exists")
@patch("app.prompts.prompt_manager.os.listdir")
def test_load_prompts_success(mock_listdir, mock_exists, valid_yaml_str):
    mock_exists.return_value = True
    mock_listdir.return_value = ["qa_bot.yaml", "summary_bot.yml", "ignore_me.txt"]

    m_open = mock_open(read_data=valid_yaml_str)

    manager = PromptManager(registry_path="/fake/registry/path")

    with patch("app.prompts.prompt_manager.open", m_open):
        manager.load_prompts()

    assert "qa_bot" in manager._registry
    assert "summary_bot" in manager._registry
    assert "ignore_me" not in manager._registry

    template = manager.get("qa_bot")
    assert template.system_prompt == "You are a helpful assistant."

@patch("app.prompts.prompt_manager.os.path.exists")
def test_load_prompts_missing_directory(mock_exists):
    mock_exists.return_value = False

    manager = PromptManager(registry_path="/fake/non_existent/dir")

    with pytest.raises(FileNotFoundError, match="Registry path does not exist."):
        manager.load_prompts()

@patch("app.prompts.prompt_manager.os.path.exists")
@patch("app.prompts.prompt_manager.os.listdir")
def test_load_prompts_skips_empty_file(mock_listdir, mock_exists, caplog):
    mock_exists.return_value = True
    mock_listdir.return_value = ["empty.yaml"]

    m_open = mock_open(read_data="")
    manager = PromptManager(registry_path="/fake/registry")

    with patch("app.prompts.prompt_manager.open", m_open), caplog.at_level("WARNING"):
        manager.load_prompts()

    assert "Skipping empty prompt file: empty.yaml" in caplog.text
    assert "empty" not in manager._registry

@pytest.mark.parametrize(
    "invalid_raw_content, expected_cause",
    [
        ("{invalid: yaml : syntax_error", yaml.YAMLError),
        ("system_prompt: 'Missing user template'", KeyError),
        ("system_prompt: 123\nuser_template: 'Wrong types'", ValidationError),
    ],
    ids=["malformed_yaml", "missing_keys", "pydantic_validation_error"]
)
@patch("app.prompts.prompt_manager.os.path.exists")
@patch("app.prompts.prompt_manager.os.listdir")
def test_load_prompts_raises_runtime_error_on_bad_files(
        mock_listdir, mock_exists, invalid_raw_content, expected_cause
):
    mock_exists.return_value = True
    mock_listdir.return_value = ["bad_template.yaml"]

    m_open = mock_open(read_data=invalid_raw_content)
    manager = PromptManager(registry_path="/fake/registry")

    with patch("app.prompts.prompt_manager.open", m_open), pytest.raises(RuntimeError) as exc_info:
        manager.load_prompts()

    assert "Malformed prompt file bad_template.yaml" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, expected_cause)

def test_get_prompt_success():
    manager = PromptManager()
    template = PromptTemplate(system_prompt="sys", user_template="user")
    manager._registry["exist_bot"] = template
    assert manager.get("exist_bot") == template

def test_get_prompt_not_found():
    manager = PromptManager()
    with pytest.raises(PromptNotFoundError):
        manager.get("ghost_template")