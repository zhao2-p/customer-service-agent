import yaml

from backend.app.core.paths import get_abs_path


def _load_yaml_config(config_relative_path: str, encoding: str = "utf-8"):
    # 返回一个字典，内容是配置文件内容，键为配置项名称，值为配置项值。
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


def load_memory_config():
    # 长期记忆配置单独拆分，避免把新增配置硬塞进既有 agent 配置里。
    return _load_yaml_config("config/memory.yml")


# 模块加载时就把配置读入内存，后续其他模块可以直接 import 使用。
# 所得到的对象都是配置文件 yaml 的内容。
rag_conf = load_rag_config()        # 得到 rag 配置
chroma_conf = load_chroma_config()
prompts_conf = load_prompts_config()    # 得到提示词模板路径字典
agent_conf = load_agent_config()
memory_conf = load_memory_config()
