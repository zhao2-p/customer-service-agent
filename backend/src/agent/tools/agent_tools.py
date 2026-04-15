import os
import random

from langchain_core.tools import tool

from backend.src.agent.rag.rag_service import RagSummarizeService
from backend.src.core.config import agent_conf
from backend.src.core.logger import logger
from backend.src.core.paths import get_abs_path


rag = RagSummarizeService()

user_ids = ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008", "1009", "1010"]
month_arr = [
    "2025-01",
    "2025-02",
    "2025-03",
    "2025-04",
    "2025-05",
    "2025-06",
    "2025-07",
    "2025-08",
    "2025-09",
    "2025-10",
    "2025-11",
    "2025-12",
]

# 这里用内存字典模拟外部系统数据，第一次读取 CSV 后会缓存在进程里。
external_data: dict[str, dict[str, dict[str, str]]] = {}


@tool(description="从向量存储中检索参考资料，并基于检索结果生成总结回答")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)


@tool(description="获取指定城市的天气，并以字符串形式返回")
def get_weather(city: str) -> str:
    return f"城市{city}天气为晴天，气温26摄氏度，空气湿度50%，南风3级，AQI21，未来24小时降雨概率极低"


@tool(description="获取用户所在城市名称，并以纯字符串形式返回")
def get_user_location() -> str:
    return random.choice(["深圳", "合肥", "杭州"])


@tool(description="获取用户ID，并以纯字符串形式返回")
def get_user_id() -> str:
    return random.choice(user_ids)


@tool(description="获取当前月份，并以纯字符串形式返回")
def get_current_month() -> str:
    return random.choice(month_arr)


def generate_external_data():
    # 第一次调用时把 CSV 读入内存，后续直接复用，避免重复读文件。
    if external_data:
        return

    external_data_path = get_abs_path(agent_conf["external_data_path"])
    if not os.path.exists(external_data_path):
        raise FileNotFoundError(f"external data file not found: {external_data_path}")

    with open(external_data_path, "r", encoding="utf-8") as file:
        for line in file.readlines()[1:]:
            arr = line.strip().split(",")

            user_id = arr[0].replace('"', "")
            feature = arr[1].replace('"', "")
            efficiency = arr[2].replace('"', "")
            consumables = arr[3].replace('"', "")
            comparison = arr[4].replace('"', "")
            time = arr[5].replace('"', "")

            if user_id not in external_data:
                external_data[user_id] = {}

            external_data[user_id][time] = {
                "特征": feature,
                "效率": efficiency,
                "耗材": consumables,
                "对比": comparison,
            }


@tool(description="从外部系统中获取指定用户在指定月份的使用记录，未命中则返回空字符串")
def fetch_external_data(user_id: str, month: str) -> str | dict[str, str]:
    generate_external_data()

    try:
        return external_data[user_id][month]
    except KeyError:
        logger.warning("[fetch_external_data] missing record for user_id=%s month=%s", user_id, month)
        return ""


@tool(description="无入参无返回值，调用后为报告生成场景注入上下文标记")
def fill_context_for_report():
    return "fill_context_for_report called"
