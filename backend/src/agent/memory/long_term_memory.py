import re
from typing import Any

from backend.src.core.config import memory_conf
from backend.src.core.logger import logger
from backend.src.infra.memory.sqlite_store import SQLiteMemoryStore


class LongTermMemoryService:
    def __init__(self):
        self.store = SQLiteMemoryStore()
        self.max_injected_memories = memory_conf["max_injected_memories"]
        self.enable_rule_based_extract = memory_conf["enable_rule_based_extract"]

    def build_memory_context(self, user_id: str, query: str) -> str:
        profile = self.store.get_user_profile(user_id)
        memories = self.retrieve_memories(user_id, query)

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

    def retrieve_memories(self, user_id: str, query: str) -> list[dict[str, Any]]:
        query_keywords = []
        for item in re.split(r"[\s,，。！；:：]+", query):
            if item:
                query_keywords.append(item)

        all_memories = self.store.list_user_memories(user_id)

        if not query_keywords:
            return all_memories[: self.max_injected_memories]

        matched_memories: list[dict[str, Any]] = []
        for memory in all_memories:
            if any(keyword in memory["content"] for keyword in query_keywords):
                matched_memories.append(memory)

        if matched_memories:
            return matched_memories[: self.max_injected_memories]

        return all_memories[: self.max_injected_memories]

    def extract_and_save(self, user_id: str, query: str, final_answer: str):
        if not self.enable_rule_based_extract:
            return

        profile_fields, memories = self.extract_candidate_memories(query, final_answer)
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
            "[LongTermMemoryService.extract_and_save] user_id=%s profile_updated=%s memories_saved=%s",
            user_id,
            bool(profile_fields),
            saved_count,
        )

    def extract_candidate_memories(self, query: str, final_answer: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        del final_answer

        profile_fields: dict[str, Any] = {}
        memories: list[dict[str, Any]] = []

        location_match = re.search(r"我住在([^\s，。！；]{2,10})", query)
        if location_match:
            profile_fields["location"] = location_match.group(1)

        name_match = re.search(r"我叫([^\s，。！；]{2,10})", query)
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
    service = LongTermMemoryService()
    demo_user_id = "memory-service-demo-user"
    demo_query = "我住在杭州，家里有猫，预算3000元以内，我更看重静音和拖地，记住这个偏好。"

    service.extract_and_save(demo_user_id, demo_query, "已为你记录偏好。")
    logger.info("[long_term_memory.__main__] context=%s", service.build_memory_context(demo_user_id, demo_query))
