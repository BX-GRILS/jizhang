"""数据库操作层 — SQLite 的初始化与所有 CRUD。

数据库文件位于用户主目录 ~/.finance-cli/data.db
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict

from finance.models import DEFAULT_CATEGORIES

# 数据库路径：用户主目录下的隐藏文件夹
DB_DIR = os.path.join(os.path.expanduser("~"), ".finance-cli")
DB_PATH = os.path.join(DB_DIR, "data.db")


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（开启外键约束，返回行可用列名访问）。"""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _get_category_id(cursor, category_name: str) -> Optional[int]:
    """根据分类名查询 ID，不存在返回 None。"""
    row = cursor.execute(
        "SELECT id FROM categories WHERE name = ?", (category_name,)
    ).fetchone()
    return row["id"] if row else None


# ============================================================
# 初始化
# ============================================================

def init_db() -> None:
    """创建 categories 和 records 表，并写入 6 个默认分类（幂等）。

    首次运行自动建库建表，后续运行不会重复写入分类。
    """
    conn = _get_conn()
    cursor = conn.cursor()

    # ---- 分类表 ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # ---- 账目表 ----
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            category_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    # ---- 写入默认分类（幂等：已存在则忽略） ----
    for cat_name in DEFAULT_CATEGORIES:
        cursor.execute(
            "INSERT OR IGNORE INTO categories (name) VALUES (?)",
            (cat_name,),
        )

    conn.commit()
    conn.close()


# ============================================================
# CRUD
# ============================================================

def add_record(amount: float, category_name: str, date: str, note: str = "") -> int:
    """新增一笔账目。

    参数：
        amount        — 金额（正数，支出）
        category_name — 分类名称，必须存在于 categories 表中
        date          — 日期，格式 YYYY-MM-DD
        note          — 备注，可选

    返回：新记录的 ID

    如果分类名不存在，抛出 ValueError。
    """
    conn = _get_conn()
    cursor = conn.cursor()

    # 查找分类 ID
    cat_id = _get_category_id(cursor, category_name)
    if cat_id is None:
        conn.close()
        raise ValueError(
            f"分类 '{category_name}' 不存在。可选分类：{', '.join(DEFAULT_CATEGORIES)}"
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO records (amount, category_id, record_date, note, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (amount, cat_id, date, note, now),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def list_records(month: Optional[str] = None, category_name: Optional[str] = None) -> List[Dict]:
    """查询账目列表，按日期降序排列。

    参数：
        month         — 月份筛选，格式 'YYYY-MM'；None 表示不过滤
        category_name — 分类名称筛选；None 表示不过滤

    返回：list[dict]，每项包含 id, amount, category_id, record_date,
          note, created_at, category_name
    """
    conn = _get_conn()
    cursor = conn.cursor()

    sql = """
        SELECT r.id, r.amount, r.category_id, r.record_date,
               r.note, r.created_at, c.name AS category_name
        FROM records r
        JOIN categories c ON r.category_id = c.id
        WHERE 1=1
    """
    params: List[str] = []

    if month:
        sql += " AND r.record_date LIKE ?"
        params.append(f"{month}%")

    if category_name:
        sql += " AND c.name = ?"
        params.append(category_name)

    sql += " ORDER BY r.record_date DESC, r.id DESC"

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_record(record_id: int) -> bool:
    """删除一笔账目。

    返回：True 表示删除成功，False 表示未找到该 ID。
    """
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def get_stats(month: Optional[str] = None) -> List[Dict]:
    """按分类统计支出。

    参数：
        month — 月份筛选，格式 'YYYY-MM'；None 表示全部数据

    返回：list[dict]，每项包含 category_name, total（总金额）, count（笔数）
          按 total 降序排列
    """
    conn = _get_conn()
    cursor = conn.cursor()

    sql = """
        SELECT c.name AS category_name,
               COALESCE(SUM(r.amount), 0) AS total,
               COUNT(r.id) AS count
        FROM categories c
        LEFT JOIN records r ON c.id = r.category_id
    """
    params: List[str] = []

    if month:
        sql += " AND r.record_date LIKE ?"
        params.append(f"{month}%")

    sql += " GROUP BY c.id ORDER BY total DESC"

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
