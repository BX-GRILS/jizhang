"""Streamlit Web 界面 — 个人记账助手。"""

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
from datetime import date

from finance.database import init_db, add_record, list_records, delete_record, get_stats
from finance.models import DEFAULT_CATEGORIES

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(page_title="个人记账助手", page_icon="💰", layout="wide")
st.title("💰 个人记账助手")

# 中文字体（Windows 优先使用 SimHei）
matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei"]
matplotlib.rcParams["axes.unicode_minus"] = False

# 启动时初始化数据库
init_db()

# ============================================================
# 侧边栏导航
# ============================================================
st.sidebar.markdown("## 📋 导航")
page = st.sidebar.radio("选择功能", ["添加记录", "账目列表", "分类统计"])

# ============================================================
# 1. 添加记录
# ============================================================
if page == "添加记录":
    st.header("📝 添加记录")

    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("金额（元）", min_value=0.01, step=0.01, format="%.2f")
            category = st.selectbox("分类", DEFAULT_CATEGORIES)
        with col2:
            record_date = st.date_input("日期", value=date.today())
            note = st.text_input("备注", placeholder="选填，如：午餐外卖")

        if st.form_submit_button("✅ 提交"):
            if amount <= 0:
                st.error("金额必须大于 0")
            else:
                rec_id = add_record(
                    amount=amount,
                    category_name=category,
                    date=record_date.strftime("%Y-%m-%d"),
                    note=note,
                )
                st.success(f"已添加！记录 ID：{rec_id}")
                st.rerun()

# ============================================================
# 2. 账目列表
# ============================================================
elif page == "账目列表":
    st.header("📋 账目列表")

    # ---- 筛选区 ----
    col1, col2 = st.columns(2)
    with col1:
        month = st.text_input(
            "按月份筛选",
            placeholder="YYYY-MM（如 2026-07），留空=全部",
        )
    with col2:
        category_filter = st.selectbox(
            "按分类筛选",
            ["全部"] + DEFAULT_CATEGORIES,
        )

    # 查询
    month_arg = month.strip() if month.strip() else None
    cat_arg = category_filter if category_filter != "全部" else None
    records = list_records(month=month_arg, category_name=cat_arg)

    # ---- 汇总 ----
    if records:
        total = sum(r["amount"] for r in records)
        st.metric("筛选结果", f"{len(records)} 笔，合计 ¥{total:,.2f}")

    # ---- 表格 ----
    if records:
        table_data = [
            {
                "ID": r["id"],
                "日期": r["record_date"],
                "分类": r["category_name"],
                "金额": f"¥{r['amount']:,.2f}",
                "备注": r["note"],
            }
            for r in records
        ]
        st.dataframe(table_data, use_container_width=True, hide_index=True)
    else:
        st.info("暂无记录，去添加一笔吧！")

    # ---- 删除 ----
    st.divider()
    st.subheader("🗑️ 删除记录")

    col1, col2 = st.columns([1, 3])
    with col1:
        delete_id = st.number_input("输入要删除的记录 ID", min_value=1, step=1)
    with col2:
        st.write("")
        st.write("")
        if st.button("🔍 查询"):
            target = list_records()
            target = [r for r in target if r["id"] == delete_id]
            if target:
                st.session_state["del_target"] = target[0]
            else:
                st.warning(f"未找到 ID 为 {delete_id} 的记录")
                st.session_state.pop("del_target", None)

    if "del_target" in st.session_state and st.session_state["del_target"]:
        t = st.session_state["del_target"]
        st.warning(
            f"确认删除：**{t['record_date']}** | {t['category_name']} | "
            f"¥{t['amount']:,.2f} | {t['note'] or '无备注'}？"
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ 确认删除", type="primary"):
                delete_record(delete_id)
                st.success("已删除！")
                st.session_state.pop("del_target", None)
                st.rerun()
        with c2:
            if st.button("❌ 取消"):
                st.session_state.pop("del_target", None)
                st.rerun()

# ============================================================
# 3. 分类统计
# ============================================================
elif page == "分类统计":
    st.header("📊 分类统计")

    month_input = st.text_input(
        "统计月份",
        placeholder="YYYY-MM（如 2026-07），留空=全部",
        key="stats_month",
    )
    month_arg = month_input.strip() if month_input.strip() else None
    stats = get_stats(month=month_arg)

    if not stats:
        st.info("暂无数据可供统计")
    else:
        grand_total = sum(s["total"] for s in stats)

        # ---- 统计表 ----
        table_data = []
        for s in stats:
            pct = (s["total"] / grand_total * 100) if grand_total > 0 else 0
            table_data.append({
                "分类": s["category_name"],
                "笔数": s["count"],
                "合计金额": f"¥{s['total']:,.2f}",
                "占比": f"{pct:.1f}%",
            })
        table_data.append({
            "分类": "**合计**",
            "笔数": sum(s["count"] for s in stats),
            "合计金额": f"¥{grand_total:,.2f}",
            "占比": "100.0%",
        })
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # ---- 柱状图 ----
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
        categories_list = [s["category_name"] for s in stats]
        totals = [s["total"] for s in stats]

        fig, ax = plt.subplots(figsize=(8, 4))
        bars = ax.bar(categories_list, totals, color=colors)
        ax.set_xlabel("分类")
        ax.set_ylabel("金额（元）")
        title = f"分类支出统计（{month_arg}）" if month_arg else "分类支出统计（全部）"
        ax.set_title(title)

        for bar, val in zip(bars, totals):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height(),
                    f"¥{val:,.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        st.pyplot(fig)
