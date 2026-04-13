from backend.app.core.config import prompts_conf
from backend.app.core.logger import logger
from backend.app.core.paths import get_abs_path

# 返回一个字符串，该字符串是配置文件中指定的提示词内容。
def _load_prompt(config_key: str, log_prefix: str) -> str:
    # Prompt 文件路径来自配置文件，这里统一做读取和异常处理。
    try:
        prompt_path = get_abs_path(prompts_conf[config_key])    # 获取配置文件里的路径。
    except KeyError as exc:
        logger.error("[%s] missing config key: %s", log_prefix, config_key)
        raise exc

    try:
        with open(prompt_path, "r", encoding="utf-8") as file:  # 根据路径读取文件。
            return file.read()                                  # 返回文件内容。
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


def append_memory_context(base_prompt: str, memory_context: str) -> str:
    # 长期记忆并不等价于历史消息，这里把它拼成一个独立的提示块，
    # 方便模型区分“系统规则”和“已知用户事实”，也方便后续替换成更复杂的注入策略。
    if not memory_context:
        return base_prompt

    return f"{base_prompt}\n\n{memory_context}\n"
