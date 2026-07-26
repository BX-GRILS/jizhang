"""数据模型定义。"""

from dataclasses import dataclass, field
from typing import Optional

# 预设的 6 个支出分类
DEFAULT_CATEGORIES = ["餐饮", "交通", "购物", "娱乐", "居住", "其他"]


@dataclass
class Category:
    """支出分类。

    id   — 数据库主键
    name — 分类名称
    """

    id: int
    name: str


@dataclass
class Record:
    """一笔记账记录。

    id            — 数据库主键
    amount        — 金额（支出，正数）
    category_id   — 关联 Category.id
    record_date   — 记账日期，格式 YYYY-MM-DD
    note          — 备注，可为空
    created_at    — 记录创建时间
    category_name — 运行时填充的分类名称，非数据库字段
    """

    id: int
    amount: float
    category_id: int
    record_date: str
    note: str = ""
    created_at: Optional[str] = None
    category_name: str = ""
