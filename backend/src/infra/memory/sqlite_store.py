import json
import os
import sqlite3
from datetime import datetime
from typing import Any

from backend.src.core.config import memory_conf
from backend.src.core.logger import logger
from backend.src.core.paths import get_abs_path


class SQLiteMemoryStore:
    def __init__(self):
        # 长期记忆先落在本地 SQLite 中，便于快速验证跨会话持久化能力。
        self.db_path = get_abs_path(memory_conf["sqlite_path"])
        self._ensure_parent_dir()
        self._init_tables()

    def _ensure_parent_dir(self):
        # SQLite 文件所在目录可能还不存在，这里提前创建，避免首次写入时报错。
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        # 统一在这里打开连接，并启用 Row 工厂，便于后续按字段名读取。
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    # 初始化表结构
    def _init_tables(self):
        # 第一版先维护两张表：
        # 1. user_profiles：保存稳定、结构化的用户画像字段。
        # 2. user_memories：保存较自由的长期记忆条目，支持后续扩展检索能力。
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    name TEXT DEFAULT '',
                    location TEXT DEFAULT '',
                    product_model TEXT DEFAULT '',
                    home_type TEXT DEFAULT '',
                    has_pet INTEGER DEFAULT 0,
                    budget_range TEXT DEFAULT '',
                    preferences_json TEXT DEFAULT '[]',
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    importance INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_memories_user_id
                ON user_memories(user_id)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_memories_user_type
                ON user_memories(user_id, memory_type)
                """
            )
            connection.commit()
        finally:
            connection.close()

    # 获取用户画像
    def get_user_profile(self, user_id: str) -> dict[str, Any]:
        # 如果画像尚未创建，则返回空画像，调用方无需关心数据库是否已有记录。
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return {
                    "user_id": user_id,
                    "name": "",
                    "location": "",
                    "product_model": "",
                    "home_type": "",
                    "has_pet": False,
                    "budget_range": "",
                    "preferences": [],
                    "updated_at": "",
                }

            return {
                "user_id": row["user_id"],
                "name": row["name"],
                "location": row["location"],
                "product_model": row["product_model"],
                "home_type": row["home_type"],
                "has_pet": bool(row["has_pet"]),
                "budget_range": row["budget_range"],
                "preferences": json.loads(row["preferences_json"] or "[]"),
                "updated_at": row["updated_at"],
            }
        finally:
            connection.close()

    # 更新用户画像
    def upsert_user_profile(self, user_id: str, fields: dict[str, Any]):
        # 画像字段是逐步累积的，这里采用“读-合并-写回”的方式，避免覆盖已有信息。
        current = self.get_user_profile(user_id)
        merged_preferences = list(current["preferences"])
        for item in fields.get("preferences", []):
            if item and item not in merged_preferences:
                merged_preferences.append(item)

        merged = {
            "name": fields.get("name", current["name"]),
            "location": fields.get("location", current["location"]),
            "product_model": fields.get("product_model", current["product_model"]),
            "home_type": fields.get("home_type", current["home_type"]),
            "has_pet": int(fields.get("has_pet", current["has_pet"])),
            "budget_range": fields.get("budget_range", current["budget_range"]),
            "preferences_json": json.dumps(merged_preferences, ensure_ascii=False),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO user_profiles (
                    user_id, name, location, product_model, home_type, has_pet,
                    budget_range, preferences_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    location = excluded.location,
                    product_model = excluded.product_model,
                    home_type = excluded.home_type,
                    has_pet = excluded.has_pet,
                    budget_range = excluded.budget_range,
                    preferences_json = excluded.preferences_json,
                    updated_at = excluded.updated_at
                """,
                (
                    user_id,
                    merged["name"],
                    merged["location"],
                    merged["product_model"],
                    merged["home_type"],
                    merged["has_pet"],
                    merged["budget_range"],
                    merged["preferences_json"],
                    merged["updated_at"],
                ),
            )
            connection.commit()
        finally:
            connection.close()

    # 列出用户记忆条目
    def list_user_memories(self, user_id: str) -> list[dict[str, Any]]:
        # 记忆条目按更新时间倒序返回，方便优先注入最新、最可能有用的条目。
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, user_id, memory_type, content, source, importance, created_at, updated_at, is_active
                FROM user_memories
                WHERE user_id = ? AND is_active = 1
                ORDER BY updated_at DESC, id DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()

    # 判断记忆条目是否存在
    def memory_exists(self, user_id: str, memory_type: str, content: str) -> bool:
        # 第一版去重策略使用“同一用户 + 同类型 + 同内容”的精确匹配，简单但稳定。
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM user_memories
                WHERE user_id = ? AND memory_type = ? AND content = ? AND is_active = 1
                LIMIT 1
                """,
                (user_id, memory_type, content),
            )
            return cursor.fetchone() is not None
        finally:
            connection.close()

    # 添加用户记忆条目
    def add_memory(
        self,
        user_id: str,
        memory_type: str,
        content: str,
        source: str = "rule",
        importance: int = 1,
    ):
        # 长期记忆允许逐条追加，后续如需支持覆盖和纠错，可在这一层扩展。
        now = datetime.now().isoformat(timespec="seconds")
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO user_memories (
                    user_id, memory_type, content, source, importance, created_at, updated_at, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (user_id, memory_type, content, source, importance, now, now),
            )
            connection.commit()
        finally:
            connection.close()


if __name__ == "__main__":
    # 模块级测试代码：
    # 直接运行 `python -m backend.src.infra.memory.sqlite_store`，
    # 可以验证建表、画像写入、记忆写入和读取是否正常。
    store = SQLiteMemoryStore()
    demo_user_id = "memory-store-demo-user"

    store.upsert_user_profile(
        demo_user_id,
        {
            "location": "杭州",
            "preferences": ["静音", "拖地能力"],
            "budget_range": "3000以内",
        },
    )
    if not store.memory_exists(demo_user_id, "issue_context", "上次咨询过跨门槛能力"):
        store.add_memory(demo_user_id, "issue_context", "上次咨询过跨门槛能力")

    logger.info("[sqlite_store.__main__] profile=%s", store.get_user_profile(demo_user_id))
    logger.info("[sqlite_store.__main__] memories=%s", store.list_user_memories(demo_user_id))
