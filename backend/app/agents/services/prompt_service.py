from backend.app.core.config import prompts_conf
from backend.app.core.logger import logger
from backend.app.core.paths import get_abs_path


def _load_prompt(config_key: str, log_prefix: str) -> str:
    # Prompt 文件路径来自配置文件，这里统一做读取和异常处理。
    try:
        prompt_path = get_abs_path(prompts_conf[config_key])
    except KeyError as exc:
        logger.error("[%s] missing config key: %s", log_prefix, config_key)
        raise exc

    try:
        with open(prompt_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as exc:
        logger.error("[%s] failed to load prompt: %s", log_prefix, str(exc))
        raise exc


def load_system_prompts() -> str:
    # Agent 默认使用的系统提示词。
    return _load_prompt("main_prompt_path", "load_system_prompts")


def load_rag_prompts() -> str:
    # RAG 总结链使用的提示词。
    return _load_prompt("rag_summarize_prompt_path", "load_rag_prompts")


def load_report_prompts() -> str:
    # 报告生成场景专用提示词。
    return _load_prompt("report_prompt_path", "load_report_prompts")
