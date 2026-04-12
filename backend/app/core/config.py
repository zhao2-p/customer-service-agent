import yaml

from backend.app.core.paths import get_abs_path


def _load_yaml_config(config_relative_path: str, encoding: str = "utf-8"):
    # 所有 YAML 配置统一从这里读取，避免各处重复拼路径。
    with open(get_abs_path(config_relative_path), "r", encoding=encoding) as file:
        return yaml.load(file, Loader=yaml.FullLoader)


def load_rag_config():
    return _load_yaml_config("config/rag.yml")


def load_chroma_config():
    return _load_yaml_config("config/chroma.yml")


def load_prompts_config():
    return _load_yaml_config("config/prompts.yml")


def load_agent_config():
    return _load_yaml_config("config/agent.yml")


# 模块加载时就把配置读入内存，后续其他模块可以直接 import 使用。
rag_conf = load_rag_config()
chroma_conf = load_chroma_config()
prompts_conf = load_prompts_config()
agent_conf = load_agent_config()
