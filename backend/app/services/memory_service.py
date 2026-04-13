import re
from typing import Any

from backend.app.core.config import memory_conf
from backend.app.core.logger import logger
from backend.app.infra.memory.sqlite_store import SQLiteMemoryStore


class MemoryService:
    def __init__(self):
        # 长期记忆服务负责三件事：
        # 1. 读取用户长期记忆并格式化为模型可消费的上下文。
        # 2. 在回答完成后从本轮内容中抽取候选长期记忆。
        # 3. 将抽取结果持久化到存储层。
        self.store = SQLiteMemoryStore()
        self.max_injected_memories = memory_conf["max_injected_memories"]
        self.enable_rule_based_extract = memory_conf["enable_rule_based_extract"]

    # 根据用户问题，构造可注入的长期记忆上下文
    def build_memory_context(self, user_id: str, query: str) -> str:
        # 第一版注入策略采用“结构化画像 + 相关记忆摘要”的形式，
        # 这样既能让模型感知长期信息，又不会把所有历史对话直接塞进上下文。

        profile = self.store.get_user_profile(user_id)      # 获取用户画像
        memories = self.retrieve_memories(user_id, query)   # 获取相关记忆摘要

        # 格式化成模型可消费的格式
        lines: list[str] = []
        if profile["name"]:
            lines.append(f"- 用户称呼：{profile['name']}")
        if profile["location"]:
            lines.append(f"- 所在城市：{profile['location']}")
        if profile["product_model"]:
            lines.append(f"- 设备型号：{profile['product_model']}")
        if profile["home_type"]:
            lines.append(f"- 户型：{profile['home_type']}")
        if profile["has_pet"]:
            lines.append("- 家庭情况：有宠物")
        if profile["budget_range"]:
            lines.append(f"- 预算范围：{profile['budget_range']}")
        if profile["preferences"]:
            lines.append(f"- 已知偏好：{'、'.join(profile['preferences'])}")

        for item in memories[: self.max_injected_memories]:
            lines.append(f"- 历史记忆（{item['memory_type']}）：{item['content']}")

        if not lines:
            return ""

        return "[长期记忆]\n" + "\n".join(lines)

    # 根据用户的问题，从长期记忆中找出相关的历史记忆，仅简单基于字符串是否包含关键词的匹配检索。
    def retrieve_memories(self, user_id: str, query: str) -> list[dict[str, Any]]:
        # 第一版暂不引入向量检索，而是用轻量关键词匹配做相关性过滤。
        # 如果当前 query 无明显关键词命中，则回退到最近更新的记忆条目。

        #先把 query 这个字符串按“空格和各种中英文标点”切开，再把切出来的空字符串去掉，最后得到一个关键词列表。
        query_keywords = []
        for item in re.split(r"[\s,，。！？；:：]+", query):
            if item:
                query_keywords.append(item)

        # 获取指定用户的所有记忆
        all_memories = self.store.list_user_memories(user_id)

        if not query_keywords:
            return all_memories[: self.max_injected_memories]   #切片操作，取前几条

        matched_memories: list[dict[str, Any]] = []     # 创建一个空列表，用来存放匹配到的记忆
        # 如果query 中有关键词，则只返回匹配的记忆
        for memory in all_memories:
            if any(keyword in memory["content"] for keyword in query_keywords):
                matched_memories.append(memory)

        if matched_memories:
            return matched_memories[: self.max_injected_memories]

        return all_memories[: self.max_injected_memories]

    # 从本轮内容里抽取可长期保存的信息
    def extract_and_save(self, user_id: str, query: str, final_answer: str):
        """
        当前是规则抽取，不是模型抽取。它会从用户输入里识别这些东西：
        我住在杭州 -> location
        我叫张三 -> name
        型号是X20 -> product_model
        预算3000元以内 -> budget_range
        有猫/有狗/有宠物 -> has_pet
        静音/拖地/续航/避障... -> preferences
        门槛/地毯/异味/不回充/卡住/噪音 -> 历史问题背景
        记住/以后推荐/下次推荐/偏好 -> 偏好类长期记忆
        也就是说，第一版不是“什么都记”，而是“命中规则才记”。
        """

        # 长期记忆写入时机放在本轮回答完成之后，便于同时参考用户输入和最终结论。
        if not self.enable_rule_based_extract:
            return

        profile_fields, memories = self.extract_candidate_memories(query, final_answer) # 提取候选长期记忆
        # 写入长期记忆
        if profile_fields:
            self.store.upsert_user_profile(user_id, profile_fields)

        saved_count = 0
        for memory in memories:
            if self.store.memory_exists(user_id, memory["memory_type"], memory["content"]):
                continue
            self.store.add_memory(
                user_id=user_id,
                memory_type=memory["memory_type"],
                content=memory["content"],
                source=memory.get("source", "rule"),
                importance=memory.get("importance", 1),
            )
            saved_count += 1

        logger.info(
            "[MemoryService.extract_and_save] user_id=%s profile_updated=%s memories_saved=%s",
            user_id,
            bool(profile_fields),
            saved_count,
        )

    # 分析用户说的话，提取出有用的信息，返回结构化信息profile_fields和非结构化记忆
    def extract_candidate_memories(self, query: str, final_answer: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        # 第一版采用规则抽取，目标是先把链路跑通。
        # 规则命中的内容偏“稳定事实”和“长期有价值的偏好/背景”，避免把一次性内容记进去。
        del final_answer        # 删除这个参数，因为当前版本暂时不用 AI 的回答来提取记忆，只看用户说了什么

        profile_fields: dict[str, Any] = {} # 创建一个空字典，用来存放用户信息
        memories: list[dict[str, Any]] = [] # 创建一个空列表，用来存放记忆

        location_match = re.search(r"我住在([^\s，。！？；]{2,10})", query)
        if location_match:
            profile_fields["location"] = location_match.group(1)

        name_match = re.search(r"我叫([^\s，。！？；]{2,10})", query)
        if name_match:
            profile_fields["name"] = name_match.group(1)

        model_match = re.search(r"(?:我买的是|我的机器是|型号是)([A-Za-z0-9\\-_]{2,30})", query)
        if model_match:
            profile_fields["product_model"] = model_match.group(1)

        budget_match = re.search(r"预算(?:在)?([0-9]{3,6}元?(?:以内|左右|以下)?)", query)
        if budget_match:
            profile_fields["budget_range"] = budget_match.group(1)

        if "有猫" in query or "有狗" in query or "有宠物" in query:
            profile_fields["has_pet"] = True

        preferences: list[str] = []
        for keyword in ["静音", "拖地", "续航", "避障", "清洁能力", "性价比"]:
            if keyword in query:
                preferences.append(keyword)
        if preferences:
            profile_fields["preferences"] = preferences

        home_type_match = re.search(r"(小户型|大户型|两室一厅|三室两厅|复式|别墅)", query)
        if home_type_match:
            profile_fields["home_type"] = home_type_match.group(1)

        if any(keyword in query for keyword in ["门槛", "地毯", "异味", "不回充", "卡住", "噪音"]):
            memories.append(
                {
                    "memory_type": "issue_context",
                    "content": query.strip(),
                    "source": "rule",
                    "importance": 2,
                }
            )

        if any(keyword in query for keyword in ["记住", "以后推荐", "下次推荐", "偏好"]):
            memories.append(
                {
                    "memory_type": "preference",
                    "content": query.strip(),
                    "source": "rule",
                    "importance": 2,
                }
            )

        return profile_fields, memories


if __name__ == "__main__":
    # 模块级测试代码：
    # 直接运行 `python -m backend.app.services.memory_service`，
    # 可验证规则抽取、持久化写入和上下文构造。
    service = MemoryService()
    demo_user_id = "memory-service-demo-user"
    demo_query = "我住在杭州，家里有猫，预算3000元以内，我更看重静音和拖地，记住这个偏好。"

    service.extract_and_save(demo_user_id, demo_query, "已为你记录偏好。")
    logger.info("[memory_service.__main__] context=%s", service.build_memory_context(demo_user_id, demo_query))
