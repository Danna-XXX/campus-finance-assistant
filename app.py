import math
import os
import uuid
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

_DIR = os.path.dirname(os.path.abspath(__file__))

from models import init_session_state, _effective_daily_budget, Expense, Challenge
from agent import chat, zone_chat
from bill_parser import parse_wechat_bill, analyze_bill_with_llm
from config import get_api_key
from demo_data import load_demo_data, DEMO_BILL_RESULT, SAMPLE_PREVIEW_ROWS

st.set_page_config(
    page_title="小花猫 · 大学生理财搭子",
    page_icon="🐱",
    layout="wide",
)

# 7-color high-contrast palette (one per spending category)
CHART_COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#C3A6FF", "#FF8E53", "#A8E6CF", "#FFB347"]

CATEGORY_TILES = {
    "一日三餐": ("🍚", "一日三餐"),
    "偶尔小资": ("🧋", "偶尔小资"),
    "日常出行": ("🚌", "日常出行"),
    "娱乐":    ("🎮", "娱乐"),
    "学习":    ("📚", "学习"),
    "日用":    ("🛒", "日用"),
    "朋友转账": ("👥", "朋友转账"),
    "家人转账": ("👨‍👩‍👧", "家人转账"),
    "房租水电": ("🏠", "房租水电"),
    "快递物流": ("📦", "快递物流"),
    "其他":    ("📋", "其他"),
}

FINANCE_CONCEPT_LINKS = {
    "年化收益率":      "https://www.cmbchina.com/",
    "复利 vs 单利":    "https://www.csrc.gov.cn/",
    "指数基金":        "https://www.csindex.com.cn/",
    "货币基金":        "https://www.cmbchina.com/",
    "定期存款":        "https://www.cmbchina.com/",
    "高收益理财的风险": "https://www.csrc.gov.cn/",
}

THEME_CSS = """
<style>
.stApp { background-color: #fef9f5; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Prevent accidental strikethrough */
.stMarkdown p, .stMarkdown li, .stCaption,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
    text-decoration: none !important;
}

.zone-header {
    background: white;
    border-radius: 12px;
    padding: 10px 14px 8px;
    margin: 4px 0 2px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    border-left: 4px solid #ff8fab;
}
.account-chip {
    background: #fef0f5;
    border-radius: 8px;
    padding: 6px 10px;
    margin: 3px 0;
    font-size: 0.82rem;
    display: flex;
    flex-direction: column;
}
.chip-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.chip-sub {
    color: #aaa;
    font-size: 0.73rem;
    margin-top: 1px;
}
.headline-box {
    background: linear-gradient(135deg, #fff5f7, #ffe8f0);
    border-radius: 16px;
    padding: 20px 24px;
    border-left: 5px solid #ff8fab;
    margin-bottom: 16px;
}
.persona-card {
    background: white;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 2px 12px rgba(255,143,171,0.15);
    text-align: center;
}
.page-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 0 10px;
    border-bottom: 1px solid #f5e0e8;
    margin-bottom: 16px;
    background: #fef9f5;
}

/* Reduce top padding so content fits in viewport without page scroll */
[data-testid="block-container"] {
    padding-top: 0.4rem !important;
    padding-bottom: 0.2rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

/* Chip quick-action buttons: pill style */
div[data-testid="column"] .stButton > button:not([kind="primary"]) {
    border-radius: 20px !important;
    font-size: 0.78rem !important;
    padding: 2px 10px !important;
    border: 1px solid #ffb3c6 !important;
    background: #fff5f7 !important;
    color: #e85d7a !important;
}
div[data-testid="column"] .stButton > button:not([kind="primary"]):hover {
    background: #ffe0eb !important;
    border-color: #ff8fab !important;
}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

init_session_state()


# ─── Navigation ──────────────────────────────────────────────────────────────

def nav_to(page: str):
    st.session_state.current_page = page
    st.rerun()


def back_btn(target: str = "main", label: str = "← 返回"):
    if st.button(label, key=f"back_{st.session_state.current_page}_{target}"):
        nav_to(target)


# ─── Chart helpers ────────────────────────────────────────────────────────────

def _pie_chart(labels, values, height=320):
    colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(labels))]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.38,
        marker_colors=colors,
        textinfo="label+percent",
        hovertemplate="%{label}: ¥%{value:.0f}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=20, b=20, l=10, r=10), height=height,
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, font=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _bar_chart(months, series: dict, height=320, mode="stack"):
    fig = go.Figure()
    for i, (cat, vals) in enumerate(series.items()):
        fig.add_trace(go.Bar(
            x=months, y=vals, name=cat,
            marker_color=CHART_COLORS[i % len(CHART_COLORS)],
            hovertemplate=f"{cat}: ¥%{{y:.0f}}<extra></extra>",
        ))
    fig.update_layout(
        barmode=mode,
        margin=dict(t=20, b=40, l=10, r=10), height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="月份", yaxis_title="支出（元）",
        legend=dict(orientation="h", y=-0.25, font=dict(size=11)),
    )
    return fig


# ─── Chat components ──────────────────────────────────────────────────────────

def render_main_chat():
    # Quick chips for main chat
    main_chips = ZONE_CHIPS.get("main", [])
    if main_chips:
        chip_cols = st.columns(len(main_chips))
        for i, (col, chip) in enumerate(zip(chip_cols, main_chips)):
            with col:
                if st.button(chip, key=f"chip_main_{i}", use_container_width=True):
                    with st.spinner("小花猫想了想..."):
                        reply = chat(chip)
                    st.rerun()

    msgs = st.session_state.messages
    chat_container = st.container(height=320)
    with chat_container:
        if not msgs:
            with st.chat_message("assistant"):
                st.markdown(
                    "hihi 我是你的花钱搭子小花猫 🐱~\n\n"
                    "我猜你应该每个月父母会固定打生活费给你吧？"
                    "还是说你已经有自己的外快了？\n\n"
                    "告诉我你的情况，我来帮你建好专属钱包～"
                )
        else:
            for msg in msgs:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    user_input = st.chat_input("跟小花猫说点什么...", key="main_chat")
    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("小花猫想了想..."):
                reply = chat(user_input)
            st.markdown(reply)
        st.rerun()


ZONE_INTRO = {
    "accounts": "关于账户有啥想问的？比如「我该从哪个账户买笔记本」～",
    "spending": "今天花了什么？或者问我这个月哪里花多了～",
    "goals": "想设个新目标？或者聊聊怎么更快攒到钱～",
    "cool_down": "清单上的东西拿不准？跟我聊聊值不值得买～",
    "finance": "想了解哪方面的理财知识？我用人话解释～",
    "alert": "想聊聊今天预算、最低资金阈值，还是看看结余走势？",
}

ZONE_CHIPS = {
    "accounts": ["我现在有多少钱？", "账户怎么分配最合理？", "哪个账户余额低了？", "自给账户怎么增加？"],
    "spending": ["今天花了多少？", "这个月哪里花最多？", "我超预算了吗？", "帮我省钱建议"],
    "goals": ["帮我设一个目标", "我的目标能完成吗？", "每月需要存多少？", "优先攒哪个目标？"],
    "cool_down": ["这个值得买吗？", "有没有替代方案？", "对我目标影响大吗？", "再等等还是现在买？"],
    "finance": ["货币基金和余额宝有啥区别？", "我现在适合理财吗？", "什么是指数基金？", "怎么开始基金定投？"],
    "main": ["帮我分析这个月的消费", "今天能买X吗？", "我现在有多少钱？", "帮我设一个储蓄目标"],
    "alert": ["今日预算设多少合适？", "我的结余趋势怎么样？", "保底资金设多少？", "我有危险吗？"],
}

FINANCE_CONCEPTS = [
    {
        "emoji": "💰", "title": "年化收益率",
        "short": "把任何时期的收益率换算成一年的收益率，便于横向对比。",
        "detail": "年化 3% 意味着存 ¥1,000 一年后得到 ¥1,030。货币基金通常年化 1.5-2.5%，沪深300指数基金长期平均约 8-10%（但有波动，不保证）。",
    },
    {
        "emoji": "📈", "title": "复利 vs 单利",
        "short": "复利是利滚利，单利只算本金的利息。",
        "detail": "¥10,000 存 10 年：单利 5% → ¥15,000；复利 5% → ¥16,289。时间越长差距越大，这就是「越早开始越好」的原因。",
    },
    {
        "emoji": "📊", "title": "指数基金",
        "short": "一次买入一篮子股票，跟着市场整体涨跌，风险低于个股。",
        "detail": "沪深300追踪A股最大300家公司，买的是「中国经济平均成绩」。不需要研究个股，适合每月定投，用时间平滑波动。",
    },
    {
        "emoji": "🏦", "title": "货币基金",
        "short": "类似活期存款，随取随用，年化约 1.5-2.5%，风险极低。",
        "detail": "余额宝、招行朝朝宝、零钱通都是货币基金。本金几乎不会亏损，适合存放短期不用但又不想浪费的钱。",
    },
    {
        "emoji": "⏰", "title": "定期存款",
        "short": "约定存一段时间，利率比活期高，到期才能取（或提前取损失利息）。",
        "detail": "3个月约 1.5%，1年约 1.75%，3年约 2.35%（各银行略有差异）。适合荣誉账户里的奖学金，不轻易动用的钱。",
    },
    {
        "emoji": "🚨", "title": "高收益理财的风险",
        "short": "年化超过 5% 且声称「无风险」的产品，大概率有问题。",
        "detail": "正规货币基金约 2%，银行定期约 2-3%。「年化 8-15% 无风险」要么是骗局，要么隐藏了极高风险。大学生要特别警惕校园贷和虚假理财 App。",
    },
]


def _compound_calc(monthly: float, years: int, annual_rate: float):
    """Returns (final_value, total_invested, interest_earned)"""
    r = annual_rate / 100 / 12
    n = years * 12
    if r > 0:
        fv = monthly * ((1 + r) ** n - 1) / r
    else:
        fv = monthly * n
    invested = monthly * n
    return round(fv, 2), round(invested, 2), round(fv - invested, 2)


def render_zone_chat(zone: str, height: int = 240):
    # Quick chips
    chips = ZONE_CHIPS.get(zone, [])
    if chips:
        chip_cols = st.columns(len(chips))
        for i, (col, chip) in enumerate(zip(chip_cols, chips)):
            with col:
                if st.button(chip, key=f"chip_{zone}_{i}", use_container_width=True):
                    with st.spinner("小花猫想了想..."):
                        zone_chat(chip, zone)
                    st.rerun()

    zone_msgs = st.session_state.zone_messages.get(zone, [])
    chat_container = st.container(height=height)
    with chat_container:
        if not zone_msgs:
            with st.chat_message("assistant"):
                st.markdown(ZONE_INTRO.get(zone, "有什么想聊的？"))
        else:
            for msg in zone_msgs:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

    user_input = st.chat_input("问小花猫...", key=f"zone_{zone}")
    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("小花猫想了想..."):
                reply = zone_chat(user_input, zone)
            st.markdown(reply)
        st.rerun()


# ─── Bill helpers ─────────────────────────────────────────────────────────────

def _apply_bill_analysis(result: dict):
    suggested = result.get("suggested_accounts", {})

    if "survival" in suggested:
        s = suggested["survival"]
        acc = st.session_state.accounts["survival"]
        if s.get("monthly_income", 0) > 0:
            acc.monthly_income = float(s["monthly_income"])
            acc.balance = float(s["monthly_income"])
            acc.income_type = "fixed"

    if "independence" in suggested:
        s = suggested["independence"]
        acc = st.session_state.accounts["independence"]
        if s.get("balance", 0) > 0:
            acc.balance = float(s["balance"])
        if s.get("monthly_income", 0) > 0:
            acc.monthly_income = float(s["monthly_income"])
        if s.get("income_type"):
            acc.income_type = s["income_type"]

    if "achievement" in suggested:
        s = suggested["achievement"]
        acc = st.session_state.accounts["achievement"]
        if s.get("balance", 0) > 0:
            acc.balance = float(s["balance"])
            acc.income_type = "one_time"

    persona = result.get("persona", {})
    summary = result.get("full_summary", {})
    summary_text = summary.get("summary_text", "账单解析完成，账户已更新。")
    persona_type = persona.get("type", "")
    full_msg = summary_text + (
        f"\n\n**消费画像：** {persona_type} {persona.get('emoji','')} — {', '.join(persona.get('tips', [])[:1])}"
        if persona_type else ""
    )
    st.session_state.messages.append({"role": "assistant", "content": full_msg})
    st.session_state.onboarding_done = True


def _show_bill_report(result: dict):
    headline = result.get("headline", "")
    if headline:
        st.markdown(
            f'<div class="headline-box"><span style="font-size:1.4rem">🔥</span> '
            f'<b>小花猫发现——</b><br><br>'
            f'<span style="font-size:1.05rem">{headline}</span></div>',
            unsafe_allow_html=True,
        )

    monthly_agg = result.get("monthly_agg", {})
    span_months = result.get("time_span", {}).get("months", len(monthly_agg))

    tab_labels = ["📊 总览", "📈 月度趋势"]
    if span_months >= 3:
        tab_labels.append("🔄 时段对比")
    tab_labels.append("🐱 消费人格")

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    # ── Tab 1: 总览 ─────────────────────────────────────────────────────────
    with tabs[tab_idx]:
        summary = result.get("full_summary", {})
        c1, c2, c3 = st.columns(3)
        c1.metric("总收入", f"¥{summary.get('total_income', 0):,.0f}")
        c2.metric("总支出", f"¥{summary.get('total_expense', 0):,.0f}")
        c3.metric("月均支出", f"¥{summary.get('monthly_avg_expense', 0):,.0f}")

        breakdown = summary.get("category_breakdown", {})
        if breakdown:
            chart_col, text_col = st.columns([1.2, 1])
            with chart_col:
                labels = [k for k, v in breakdown.items() if v > 0]
                values = [v for k, v in breakdown.items() if v > 0]
                if labels:
                    st.plotly_chart(_pie_chart(labels, values, 340), width='stretch', key="bill_pie_chart")
            with text_col:
                st.markdown("**关键洞察**")
                for ins in summary.get("top_insights", []):
                    st.markdown(f"- {ins}")
                st.markdown("")
                st.markdown(summary.get("summary_text", ""))
    tab_idx += 1

    # ── Tab 2: 月度趋势 ────────────────────────────────────────────────────
    with tabs[tab_idx]:
        if not monthly_agg:
            st.info("暂无月度数据")
        else:
            months = sorted(monthly_agg.keys())
            totals = [monthly_agg[m]["total_expense"] for m in months]
            avg = sum(totals) / len(totals) if totals else 0

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=months, y=totals, mode="lines+markers",
                line=dict(color="#FF6B6B", width=2.5),
                marker=dict(size=8, color="#FF6B6B"),
                name="月支出",
                hovertemplate="%{x}: ¥%{y:.0f}<extra></extra>",
            ))
            fig_line.add_hline(
                y=avg, line_dash="dash", line_color="#aaa",
                annotation_text=f"均值 ¥{avg:.0f}",
                annotation_position="bottom right",
            )
            fig_line.update_layout(
                margin=dict(t=20, b=20, l=10, r=10), height=300,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="月份", yaxis_title="支出（元）",
                showlegend=False,
            )
            st.plotly_chart(fig_line, width='stretch', key="bill_trend_chart")

            all_cats = sorted({cat for m_data in monthly_agg.values() for cat in m_data.get("expense", {}).keys()})
            series = {cat: [monthly_agg[m].get("expense", {}).get(cat, 0) for m in months] for cat in all_cats}
            st.plotly_chart(_bar_chart(months, series, height=320, mode="stack"), width='stretch', key="bill_bar_chart")

            trends = result.get("trends", {})
            if trends.get("trend_text"):
                st.info(trends["trend_text"])
            col_a, col_b = st.columns(2)
            with col_a:
                if trends.get("increasing"):
                    st.markdown("📈 **增长类别：** " + "、".join(trends["increasing"]))
            with col_b:
                if trends.get("decreasing"):
                    st.markdown("📉 **减少类别：** " + "、".join(trends["decreasing"]))
    tab_idx += 1

    # ── Tab 3: 时段对比 ────────────────────────────────────────────────────
    if span_months >= 3:
        with tabs[tab_idx]:
            months_sorted = sorted(monthly_agg.keys())
            all_cats2 = sorted({cat for m_data in monthly_agg.values() for cat in m_data.get("expense", {}).keys()})

            if span_months >= 6:
                quarters: dict = {}
                for m in months_sorted:
                    q_num = (int(m[5:7]) - 1) // 3 + 1
                    q_key = f"{m[:4]}-Q{q_num}"
                    quarters.setdefault(q_key, []).append(m)
                q_labels = sorted(quarters.keys())
                series2 = {}
                for cat in all_cats2:
                    series2[cat] = [
                        sum(monthly_agg.get(m, {}).get("expense", {}).get(cat, 0) for m in quarters[q])
                        for q in q_labels
                    ]
                fig_q = _bar_chart(q_labels, series2, height=340, mode="group")
                fig_q.update_layout(title="按季度对比各类支出")
                st.plotly_chart(fig_q, width='stretch', key="bill_q_chart")
            else:
                mid = len(months_sorted) // 2
                first_half = months_sorted[:mid]
                second_half = months_sorted[mid:]
                periods = [f"{first_half[0]}～{first_half[-1]}", f"{second_half[0]}～{second_half[-1]}"]
                series2 = {}
                for cat in all_cats2:
                    v1 = sum(monthly_agg.get(m, {}).get("expense", {}).get(cat, 0) for m in first_half)
                    v2 = sum(monthly_agg.get(m, {}).get("expense", {}).get(cat, 0) for m in second_half)
                    series2[cat] = [v1, v2]
                fig_h = _bar_chart(periods, series2, height=340, mode="group")
                fig_h.update_layout(title="前半段 vs 后半段支出对比")
                st.plotly_chart(fig_h, width='stretch', key="bill_h_chart")

            trends = result.get("trends", {})
            if trends.get("trend_text"):
                st.info(trends["trend_text"])
        tab_idx += 1

    # ── Tab 4: 消费人格 ──────────────────────────────────────────────────────
    with tabs[tab_idx]:
        persona = result.get("persona", {})
        p_type = persona.get("type", "")
        p_emoji = persona.get("emoji", "🐱")

        if p_type:
            st.markdown(
                f'<div class="persona-card">'
                f'<div style="font-size:3rem">{p_emoji}</div>'
                f'<h2 style="margin:8px 0 4px; color:#ff5d8f">{p_type}</h2>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown("")

        col_a, col_b = st.columns(2)
        with col_a:
            strengths = persona.get("strengths", [])
            if strengths:
                st.markdown("#### 你做得好的地方")
                for s in strengths:
                    st.markdown(f"- {s}")
        with col_b:
            blindspots = persona.get("blindspots", [])
            if blindspots:
                st.markdown("#### 容易踩的坑")
                for b in blindspots:
                    st.markdown(f"- {b}")

        tips = persona.get("tips", [])
        if tips:
            st.markdown("#### 小花猫的建议")
            for t in tips:
                st.info(t)


# ─── LANDING PAGE ─────────────────────────────────────────────────────────────

def page_landing():
    st.markdown(
        "<div style='text-align:center; padding:40px 0 20px'>"
        "<span style='font-size:3.5rem'>🐱</span>"
        "<h1 style='margin:8px 0 4px; font-size:2rem; color:#333'>小花猫</h1>"
        "<p style='color:#999; margin:0; font-size:1rem'>大学生理财搭子 · 基于心理账户</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    # ── 人设选择 ──────────────────────────────────────────────────────────────
    st.markdown(
        "<p style='text-align:center; font-size:1rem; color:#888; margin:16px 0 10px'>先选一个搭子人设吧 👇</p>",
        unsafe_allow_html=True,
    )
    personas = [
        ("毒舌好友", "😏", "嘴损心软，损你是关心"),
        ("理性学长", "🎓", "数据说话，给你具体方案"),
        ("温柔管家", "🌸", "鼓励为主，永远站你这边"),
    ]
    current_persona = st.session_state.get("persona_style", "毒舌好友")
    pa, pb, pc = st.columns(3)
    for col, (name, emoji, desc) in zip([pa, pb, pc], personas):
        with col:
            selected = current_persona == name
            bg = "#fff5f7" if selected else "white"
            border = "2px solid #ff8fab" if selected else "1px solid #eee"
            st.markdown(
                f'<div style="background:{bg}; border-radius:12px; padding:12px 8px; text-align:center; border:{border}">'
                f'<div style="font-size:1.6rem">{emoji}</div>'
                f'<b style="font-size:0.9rem">{name}</b><br>'
                f'<span style="color:#aaa; font-size:0.75rem">{desc}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "✓ 已选" if selected else "选择",
                key=f"persona_btn_{name}",
                use_container_width=True,
                type="primary" if selected else "secondary",
            ):
                st.session_state.persona_style = name
                st.rerun()

    st.markdown(
        "<p style='text-align:center; font-size:1.1rem; color:#666; margin:20px 0 28px'>请问你想先……</p>",
        unsafe_allow_html=True,
    )

    _, c1, c2, _ = st.columns([1, 2, 2, 1])

    with c1:
        st.markdown("""
        <div style="background:white; border-radius:20px; padding:28px 20px;
                    text-align:center; box-shadow:0 4px 16px rgba(0,0,0,0.08); min-height:160px">
            <div style="font-size:2.2rem">🚀</div>
            <h3 style="margin:10px 0 6px; color:#333">快速体验核心功能</h3>
            <p style="color:#888; font-size:0.88rem; margin:0">预置一个月真实感数据<br>账户/目标/消费/冷静清单全有</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("开始体验 →", key="btn_quick", use_container_width=True, type="primary"):
            load_demo_data()
            st.rerun()

    with c2:
        st.markdown("""
        <div style="background:white; border-radius:20px; padding:28px 20px;
                    text-align:center; box-shadow:0 4px 16px rgba(0,0,0,0.08); min-height:160px">
            <div style="font-size:2.2rem">📊</div>
            <h3 style="margin:10px 0 6px; color:#333">分析我的微信账单</h3>
            <p style="color:#888; font-size:0.88rem; margin:0">导入历史账单，AI 自动画像<br>图文并茂，了解真实消费习惯<br><span style="color:#fb6f92">（后台已预置示例数据，可直接体验）</span></p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("上传账单 →", key="btn_bill", use_container_width=True):
            nav_to("bill_upload")

    st.markdown("<br><br>", unsafe_allow_html=True)
    _, rc, _ = st.columns([4, 1, 4])
    with rc:
        if st.button("重置数据", key="reset_landing"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ─── BILL UPLOAD PAGE ─────────────────────────────────────────────────────────

def page_bill_upload():
    back_btn("landing", "← 返回")
    st.markdown("## 📊 分析微信账单")
    st.divider()

    upload_mode = st.radio(
        "请选择账单来源：",
        ["上传我自己的账单（.xlsx）", "用内置示例账单体验（推荐）"],
        index=1,
        horizontal=True,
        key="upload_mode",
    )

    file_to_analyze = None
    use_demo_result = False

    if upload_mode.startswith("上传"):
        uploaded = st.file_uploader("上传微信支付账单", type=["xlsx"], key="bill_uploader")
        file_to_analyze = uploaded
    else:
        try:
            with open(os.path.join(_DIR, "sample_bill.xlsx"), "rb") as f:
                file_to_analyze = f.read()
            use_demo_result = True
            st.info("📁 使用内置示例账单（跨度为一年：2025年5月 - 2026年4月）")

            # Show representative preview rows
            st.markdown("**账单样例（部分代表性交易）：**")
            st.dataframe(pd.DataFrame(SAMPLE_PREVIEW_ROWS), hide_index=True, use_container_width=True)

        except FileNotFoundError:
            st.warning("示例账单文件未找到，请上传自己的账单。")
            uploaded = st.file_uploader("上传微信支付账单", type=["xlsx"], key="bill_fallback")
            file_to_analyze = uploaded

    if file_to_analyze:
        if st.button("🐱 开始分析", type="primary", use_container_width=True, key="btn_analyze"):
            if use_demo_result:
                # Instant: use pre-computed result
                st.session_state.bill_result = DEMO_BILL_RESULT
                _apply_bill_analysis(DEMO_BILL_RESULT)
                st.session_state.bill_analysis_done = True
            else:
                with st.spinner("小花猫正在认真分析你的账单，稍等一下～"):
                    try:
                        transactions = parse_wechat_bill(file_to_analyze)
                        if not transactions:
                            st.error("没有解析到任何交易记录，请检查账单格式。")
                            return
                        result = analyze_bill_with_llm(transactions, get_api_key())
                        st.session_state.bill_result = result
                        _apply_bill_analysis(result)
                        st.session_state.bill_analysis_done = True
                    except Exception as e:
                        st.error(f"账单解析失败：{e}")
                        return

    if st.session_state.get("bill_analysis_done") and "bill_result" in st.session_state:
        st.divider()
        _show_bill_report(st.session_state.bill_result)
        st.divider()
        st.success("我已经大致了解你的消费风格啦～账户已根据账单自动配置好！")
        if st.button("进入核心功能 →", type="primary", use_container_width=True, key="btn_enter"):
            nav_to("main")


# ─── MAIN PAGE ────────────────────────────────────────────────────────────────

def page_main():
    top_l, top_r = st.columns([8, 1])
    with top_l:
        st.markdown("<h2 style='margin:0 0 4px'>🐱 小花猫</h2>", unsafe_allow_html=True)
    with top_r:
        if st.button("← 首页", key="back_to_landing"):
            nav_to("landing")

    left, right = st.columns([1, 3])
    with left:
        _render_left_panel()
    with right:
        render_main_chat()


def _render_left_panel():
    accounts = st.session_state.accounts
    now = datetime.now()
    month_str = f"{now.year}-{now.month:02d}"
    day_str = now.strftime("%Y-%m-%d")

    persona = st.session_state.get("persona_style", "毒舌好友")
    persona_emoji = {"毒舌好友": "😏", "理性学长": "🎓", "温柔管家": "🌸"}.get(persona, "🐱")

    day_budget = _effective_daily_budget()
    today_spent = sum(
        e.amount for e in st.session_state.expenses
        if e.timestamp.startswith(day_str) and not e.is_income
    )
    pct_s = (today_spent / day_budget) if day_budget > 0 else 0
    mood = "😊" if pct_s < 0.6 else "😐" if pct_s < 0.85 else "😰" if pct_s < 1.0 else "😱"
    mood_text = {"😊": "今天花得不多", "😐": "还好，注意一下", "😰": "快超预算了！", "😱": "今天超支啦"}.get(mood, "")

    st.markdown(
        f'<div style="text-align:center; padding:6px 4px 4px; margin-bottom:2px">'
        f'<span style="font-size:1.8rem">{persona_emoji}</span>'
        f'<span style="font-size:1.1rem"> {mood}</span><br>'
        f'<span style="color:#aaa; font-size:0.68rem">{persona} · {mood_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 人设快切
    pc1, pc2, pc3 = st.columns(3)
    p_opts = [("😏", "毒舌好友"), ("🎓", "理性学长"), ("🌸", "温柔管家")]
    for col, (pemoji, pname) in zip([pc1, pc2, pc3], p_opts):
        with col:
            is_sel = persona == pname
            if st.button(
                f"✓{pemoji}" if is_sel else pemoji,
                key=f"qp_{pname}",
                help=pname,
                type="primary" if is_sel else "secondary",
                use_container_width=True,
            ):
                st.session_state.persona_style = pname
                st.rerun()

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # 6 导航按钮
    total_balance = sum(a.balance for a in accounts.values())
    month_exp = sum(
        e.amount for e in st.session_state.expenses
        if e.timestamp.startswith(month_str) and not e.is_income
    )
    n_cats = len({e.category for e in st.session_state.expenses if e.timestamp.startswith(month_str) and not e.is_income})
    n_goals = len([g for g in st.session_state.goals if g.progress_pct < 100])
    pending_count = len([c for c in st.session_state.cool_down if c.status == "pending"])
    min_reserve = st.session_state.get("min_reserve", 500.0)
    finance_ok = total_balance >= min_reserve

    nav_items = [
        ("💰 收入区", f"总余额 ¥{total_balance:,.0f}", "detail_accounts"),
        ("📊 消费记录", f"本月 ¥{month_exp:,.0f} | {n_cats} 类", "detail_spending"),
        ("🎯 储蓄目标", f"{n_goals} 个目标进行中" if n_goals else "暂无进行中目标", "detail_goals"),
        ("⏳ 购物冷静区", f"{pending_count} 条待决策" if pending_count else "清单为空 👍", "detail_cool_down"),
        ("💡 理财区", "✅ 保底达标" if finance_ok else f"保底进度 {min(total_balance/min_reserve,1)*100:.0f}%", "detail_finance"),
        ("🔔 资金预警", f"余额 ¥{total_balance:,.0f}", "detail_alert"),
    ]

    for label, caption, target in nav_items:
        if st.button(label, key=f"nav_{target}", use_container_width=True):
            nav_to(target)


# ─── DETAIL PAGES ─────────────────────────────────────────────────────────────

def _render_treemap(exps, prev_exps, unit_label: str, period_label: str, chart_key: str = ""):
    total = sum(e.amount for e in exps)
    prev_total = sum(e.amount for e in prev_exps)
    delta_str = f"{'+'if total>prev_total else ''}{total-prev_total:.0f} vs 上{unit_label}"
    st.metric(f"{period_label} 支出", f"¥{total:,.0f}", delta=delta_str,
              delta_color="inverse")

    cat_totals: dict = {}
    for e in exps:
        cat_totals[e.category] = cat_totals.get(e.category, 0) + e.amount

    if not cat_totals:
        st.info("这个时段没有支出记录～")
        return

    labels, values, parents, texts = [], [], [], []
    for cat, amt in sorted(cat_totals.items(), key=lambda x: -x[1]):
        emoji, display = CATEGORY_TILES.get(cat, ("📋", cat))
        pct = amt / total * 100 if total > 0 else 0
        labels.append(f"{emoji} {display}")
        values.append(amt)
        parents.append("")
        texts.append(f"¥{amt:.0f}<br>{pct:.1f}%")

    colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(labels))]
    fig = go.Figure(go.Treemap(
        labels=labels, values=values, parents=parents,
        text=texts, textinfo="label+text",
        marker=dict(colors=colors),
        hovertemplate="%{label}: %{text}<extra></extra>",
    ))
    fig.update_layout(height=260, margin=dict(t=10, b=10, l=10, r=10))
    _key = chart_key or period_label
    st.plotly_chart(fig, width='stretch', key=f"treemap_{_key}")

    sel_cat = st.selectbox("查看类别明细", ["（不查看）"] + list(cat_totals.keys()),
                           key=f"sp_cat_sel_{_key}")
    if sel_cat != "（不查看）":
        cat_exps = [e for e in exps if e.category == sel_cat]
        for e in sorted(cat_exps, key=lambda x: x.timestamp, reverse=True):
            st.markdown(
                f"<div style='padding:3px 0; border-bottom:1px solid #f5f5f5'>"
                f"<span style='color:#aaa;font-size:0.75rem'>{e.timestamp[:10]}</span>  "
                f"{e.description or e.category}  "
                f"<span style='color:#e74c3c'>-¥{e.amount:.0f}</span></div>",
                unsafe_allow_html=True,
            )


def page_detail_accounts():
    back_btn()
    st.markdown("### 💰 收入区")

    accounts = st.session_state.accounts
    col1, col2, col3 = st.columns([1.2, 1.5, 1.3])

    # ── 列1：余额展示 + 新收入录入 ────────────────────────────────────────────
    with col1:
        with st.container(height=500):
            for acc_id in ["survival", "independence", "achievement"]:
                acc = accounts[acc_id]
                st.markdown(
                    f"**{acc.emoji} {acc.name}**  "
                    f"<span style='color:#aaa;font-size:0.72rem'>¥{acc.balance:,.0f}</span>",
                    unsafe_allow_html=True,
                )
                with st.form(key=f"income_form_{acc_id}", clear_on_submit=True):
                    inc_date = st.date_input(
                        "日期", value=datetime.now().date(),
                        key=f"idate_{acc_id}", label_visibility="collapsed",
                    )
                    if acc_id == "independence":
                        inc_type = st.selectbox(
                            "类型", ["兼职", "实习", "接单"],
                            key=f"itype_{acc_id}", label_visibility="collapsed",
                        )
                    elif acc_id == "achievement":
                        inc_type = st.selectbox(
                            "类型", ["国家奖学金", "一等奖学金", "二等奖学金",
                                     "三等奖学金", "竞赛奖金", "助学金", "其他"],
                            key=f"itype_{acc_id}", label_visibility="collapsed",
                        )
                    else:
                        inc_type = "生活费"
                        st.caption("每月生活费")
                    inc_amount = st.number_input(
                        "金额", min_value=0.0, step=50.0,
                        key=f"iamt_{acc_id}", label_visibility="collapsed",
                    )
                    if st.form_submit_button("+ 记录", use_container_width=True):
                        if inc_amount > 0:
                            acc.balance += inc_amount
                            prefix = f"[{inc_type}] " if acc_id != "survival" else ""
                            st.session_state.expenses.append(Expense(
                                timestamp=f"{inc_date.strftime('%Y-%m-%d')} 12:00",
                                amount=inc_amount, category="收入",
                                account=acc_id,
                                description=f"{prefix}{inc_type}",
                                is_income=True,
                            ))
                            st.rerun()
                st.markdown(
                    "<hr style='margin:4px 0; border:none; border-top:1px solid #f5e0e8'>",
                    unsafe_allow_html=True,
                )

    # ── 列2：走势图 + 鼓励 ────────────────────────────────────────────────────
    with col2:
        with st.container(height=500):
            # 基石账户月收入走势
            survival_monthly: dict = {}
            for e in st.session_state.expenses:
                if e.is_income and e.account == "survival":
                    m = e.timestamp[:7]
                    survival_monthly[m] = survival_monthly.get(m, 0) + e.amount
            if survival_monthly:
                fig1 = go.Figure(go.Bar(
                    x=sorted(survival_monthly.keys()),
                    y=[survival_monthly[m] for m in sorted(survival_monthly.keys())],
                    marker_color="#96CEB4",
                    hovertemplate="%{x}: ¥%{y:.0f}<extra></extra>",
                ))
                fig1.update_layout(
                    height=120, showlegend=False,
                    margin=dict(t=4, b=4, l=4, r=4),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                )
                st.caption("🏠 基石账户（生活费）")
                st.plotly_chart(fig1, width='stretch', key="acc_survival_chart")

            # 自给账户3色柱状图（兼职/实习/接单）
            indep_by_type: dict = {}
            for e in st.session_state.expenses:
                if e.is_income and e.account == "independence":
                    m = e.timestamp[:7]
                    if m not in indep_by_type:
                        indep_by_type[m] = {"兼职": 0.0, "实习": 0.0, "接单": 0.0}
                    matched = False
                    for t in ["兼职", "实习", "接单"]:
                        if t in e.description:
                            indep_by_type[m][t] += e.amount
                            matched = True
                            break
                    if not matched:
                        indep_by_type[m]["兼职"] += e.amount

            ind_months = sorted(indep_by_type.keys())
            if ind_months:
                fig2 = go.Figure()
                type_colors = {"兼职": "#4ECDC4", "实习": "#FF6B6B", "接单": "#FFEAA7"}
                for t in ["兼职", "实习", "接单"]:
                    fig2.add_trace(go.Bar(
                        x=ind_months,
                        y=[indep_by_type[m].get(t, 0) for m in ind_months],
                        name=t, marker_color=type_colors[t],
                        hovertemplate=f"{t}: ¥%{{y:.0f}}<extra></extra>",
                    ))
                fig2.update_layout(
                    barmode="stack", height=130, showlegend=True,
                    margin=dict(t=4, b=16, l=4, r=4),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=-0.45, font=dict(size=9)),
                )
                st.caption("💪 自给账户（兼职 / 实习 / 接单）")
                st.plotly_chart(fig2, width='stretch', key="acc_indep_chart")

                ind_totals = {m: sum(indep_by_type[m].values()) for m in ind_months}
                if len(ind_months) >= 2:
                    last2 = sorted(ind_months)[-2:]
                    diff = ind_totals[last2[1]] - ind_totals[last2[0]]
                    if diff > 0:
                        st.success(f"💪 自给收入比上月多 ¥{diff:.0f}，独立感+1！")
                    elif diff < 0:
                        st.info("这月自给收入少了些，下月加油～")
                elif len(ind_months) == 1:
                    st.info("🎉 记录了第一笔自给收入，独立生活开始！")

            # 荣誉账户稀疏柱状图（带类型标注）
            achiev_records = []
            for e in st.session_state.expenses:
                if e.is_income and e.account == "achievement":
                    achiev_records.append((e.timestamp[:7], e.description, e.amount))
            if achiev_records:
                am = [r[0] for r in achiev_records]
                av = [r[2] for r in achiev_records]
                at = [r[1] for r in achiev_records]
                fig3 = go.Figure(go.Bar(
                    x=am, y=av, text=at, textposition="outside",
                    marker_color="#C3A6FF",
                    hovertemplate="%{text}: ¥%{y:.0f}<extra></extra>",
                ))
                fig3.update_layout(
                    height=120, showlegend=False,
                    margin=dict(t=20, b=4, l=4, r=4),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                )
                st.caption("🎓 荣誉账户（奖学金 / 竞赛）")
                st.plotly_chart(fig3, width='stretch', key="acc_achiev_chart")
                st.success(f"🎓 {len(achiev_records)} 笔荣誉收入，总计 ¥{sum(av):,.0f}！")

    # ── 列3：AI 问答 ──────────────────────────────────────────────────────────
    with col3:
        render_zone_chat("accounts", height=430)


def page_detail_spending():
    back_btn()
    st.markdown("### 📊 消费记录")

    now = datetime.now()
    left, right = st.columns([1.7, 1.3])

    with left:
        with st.container(height=510):
            t1, t2, t3, t4 = st.tabs(["今日", "月度", "季度", "年度"])

            with t1:
                sel_day = st.date_input("选择日期", value=now.date(), key="sp_day",
                                        label_visibility="collapsed")
                day_str = sel_day.strftime("%Y-%m-%d")
                exps = [e for e in st.session_state.expenses
                        if e.timestamp.startswith(day_str) and not e.is_income]
                prev_day = sel_day - timedelta(days=1)
                prev_exps = [e for e in st.session_state.expenses
                             if e.timestamp.startswith(prev_day.strftime("%Y-%m-%d")) and not e.is_income]
                _render_treemap(exps, prev_exps, "日", sel_day.strftime("%m月%d日"), chart_key="day")

            with t2:
                col_y, col_m = st.columns(2)
                yr = col_y.selectbox("年", range(now.year - 2, now.year + 1), index=2, key="sp_yr")
                mo = col_m.selectbox("月", range(1, 13), index=now.month - 1, key="sp_mo")
                month_str = f"{yr}-{mo:02d}"
                exps = [e for e in st.session_state.expenses
                        if e.timestamp.startswith(month_str) and not e.is_income]
                prev_mo = mo - 1 if mo > 1 else 12
                prev_yr = yr if mo > 1 else yr - 1
                prev_exps = [e for e in st.session_state.expenses
                             if e.timestamp.startswith(f"{prev_yr}-{prev_mo:02d}") and not e.is_income]
                _render_treemap(exps, prev_exps, "月", f"{yr}年{mo}月", chart_key="month")

            with t3:
                q_options = ["Q1 (1-3月)", "Q2 (4-6月)", "Q3 (7-9月)", "Q4 (10-12月)"]
                cur_q = (now.month - 1) // 3
                col_qy, col_qq = st.columns(2)
                q_yr = col_qy.selectbox("年", range(now.year - 2, now.year + 1), index=2, key="sp_qyr")
                q_sel = col_qq.selectbox("季度", q_options, index=cur_q, key="sp_q")
                q_idx = q_options.index(q_sel)
                q_months_map = {0: ["01", "02", "03"], 1: ["04", "05", "06"],
                                2: ["07", "08", "09"], 3: ["10", "11", "12"]}
                q_ms = [f"{q_yr}-{m}" for m in q_months_map[q_idx]]
                exps = [e for e in st.session_state.expenses
                        if e.timestamp[:7] in q_ms and not e.is_income]
                prev_q_idx = (q_idx - 1) % 4
                prev_q_yr = q_yr if q_idx > 0 else q_yr - 1
                prev_q_ms = [f"{prev_q_yr}-{m}" for m in q_months_map[prev_q_idx]]
                prev_exps = [e for e in st.session_state.expenses
                             if e.timestamp[:7] in prev_q_ms and not e.is_income]
                _render_treemap(exps, prev_exps, "季", f"{q_yr}年{q_sel}", chart_key="quarter")

            with t4:
                y_sel = st.selectbox("年度", range(now.year - 2, now.year + 1), index=2, key="sp_yr_only")
                exps = [e for e in st.session_state.expenses
                        if e.timestamp[:4] == str(y_sel) and not e.is_income]
                prev_exps = [e for e in st.session_state.expenses
                             if e.timestamp[:4] == str(y_sel - 1) and not e.is_income]
                _render_treemap(exps, prev_exps, "年", f"{y_sel}年", chart_key="year")

    with right:
        render_zone_chat("spending", height=430)


def page_detail_goals():
    back_btn()
    st.markdown("### 🎯 储蓄目标")

    accounts = st.session_state.accounts
    left, right = st.columns([1.5, 1.5])

    with left:
        with st.container(height=510):
            short_goals = [g for g in st.session_state.goals if g.goal_type == "short"]
            long_goals = [g for g in st.session_state.goals if g.goal_type == "long"]
            active = [g for g in st.session_state.goals if g.progress_pct < 100]
            tab_short, tab_long, tab_plan = st.tabs(["🎯 短期", "🏆 长期", "📐 储蓄方案"])

            src_opts = ["survival", "independence", "achievement"]
            src_labels = {
                "survival": "🏠 基石账户",
                "independence": "💪 自给账户",
                "achievement": "🎓 荣誉账户",
            }

            def _render_goal_row(g, prefix: str):
                c_info, c_up = st.columns([5, 1])
                with c_info:
                    st.progress(g.progress_pct / 100,
                                text=f"{g.name}  {g.progress_pct:.0f}%  差¥{g.remaining:.0f}")
                    new_src = st.selectbox(
                        "来源", src_opts,
                        index=src_opts.index(g.source_account) if g.source_account in src_opts else 1,
                        format_func=lambda x: src_labels.get(x, x),
                        key=f"src_{prefix}_{g.id}",
                        label_visibility="collapsed",
                    )
                    if new_src != g.source_account:
                        g.source_account = new_src
                        st.rerun()
                    acc = accounts.get(g.source_account)
                    if acc and acc.monthly_income > 0:
                        mos = math.ceil(g.remaining / acc.monthly_income) if g.remaining > 0 else 0
                        st.caption(f"{acc.emoji}{acc.name} ¥{acc.monthly_income:.0f}/月 → {mos}个月")
                    elif acc:
                        st.caption(f"来源：{acc.emoji}{acc.name}")
                with c_up:
                    if st.button("▲", key=f"up_{prefix}_{g.id}", help="提升优先级"):
                        g.priority += 1
                        st.rerun()
                st.markdown(
                    "<hr style='margin:2px 0; border:none; border-top:1px solid #f5e0e8'>",
                    unsafe_allow_html=True,
                )

            with tab_short:
                active_short = [g for g in short_goals if g.progress_pct < 100]
                done_short = [g for g in short_goals if g.progress_pct >= 100]
                if not active_short and not done_short:
                    st.info("还没有短期目标～告诉小花猫你想攒什么？")
                for g in sorted(active_short, key=lambda x: -x.priority):
                    _render_goal_row(g, "s")
                if done_short:
                    with st.expander(f"✅ 已完成（{len(done_short)}）"):
                        for g in done_short:
                            st.markdown(f"**{g.name}** — 完成于 {g.created_at}")
                            st.caption(f"目标金额 ¥{g.target:.0f}")

            with tab_long:
                active_long = [g for g in long_goals if g.progress_pct < 100]
                done_long = [g for g in long_goals if g.progress_pct >= 100]
                if not active_long and not done_long:
                    st.info("还没有长期目标～大目标从小步骤开始！")
                for g in sorted(active_long, key=lambda x: -x.priority):
                    _render_goal_row(g, "l")
                if done_long:
                    with st.expander(f"✅ 已完成（{len(done_long)}）"):
                        for g in done_long:
                            st.markdown(f"**{g.name}** — 完成于 {g.created_at}")
                            st.caption(f"目标金额 ¥{g.target:.0f}")

            with tab_plan:
                if not active:
                    st.info("暂无进行中的目标。")
                else:
                    plan = st.radio(
                        "储蓄方案",
                        ["⭐ 顺序存（优先级高的先满）", "⚖️ 同时存（按余额比例分配）"],
                        key="goal_plan_mode",
                    )
                    st.markdown("---")
                    sorted_active = sorted(active, key=lambda x: -x.priority)

                    if "顺序" in plan:
                        cumulative = 0
                        for g in sorted_active:
                            acc = accounts.get(g.source_account)
                            m = acc.monthly_income if acc else 0
                            mo = math.ceil(g.remaining / m) if m > 0 and g.remaining > 0 else "?"
                            cumulative_str = f"（第{cumulative+1}—{cumulative+mo}个月）" if isinstance(mo, int) else ""
                            st.markdown(f"**{g.name}** → {mo}个月完成 {cumulative_str}")
                            st.caption(f"  还差 ¥{g.remaining:.0f}，来源：{acc.emoji if acc else ''}{acc.name if acc else g.source_account}")
                            if isinstance(mo, int):
                                cumulative += mo
                    else:
                        total_rem = sum(g.remaining for g in sorted_active)
                        total_monthly = sum(
                            (accounts.get(g.source_account).monthly_income if accounts.get(g.source_account) else 0)
                            for g in sorted_active
                        )
                        if total_monthly <= 0:
                            st.warning("账户月收入为0，无法计算分配方案。")
                        else:
                            for g in sorted_active:
                                ratio = g.remaining / total_rem if total_rem > 0 else 0
                                alloc = total_monthly * ratio
                                mo = math.ceil(g.remaining / alloc) if alloc > 0 else "?"
                                st.markdown(f"**{g.name}** — 每月分 ¥{alloc:.0f}（{ratio*100:.0f}%）→ {mo}个月")

    with right:
        render_zone_chat("goals", height=430)


def page_detail_cool_down():
    back_btn()
    st.markdown("### ⏳ 购物冷静区")

    left, right = st.columns([1.3, 1.7])

    with left:
        with st.container(height=510):
            st.caption("冲动消费之前，先放这里想24小时")
            pending = [c for c in st.session_state.cool_down if c.status == "pending"]
            done = [c for c in st.session_state.cool_down if c.status != "pending"]

            if not pending:
                st.success("🎉 冷静清单是空的！说明最近没有冲动消费～")
            else:
                st.markdown(f"**待决策（{len(pending)} 件）**")
                for i, item in enumerate(pending):
                    with st.container():
                        ci, cb1, cb2 = st.columns([3, 1, 1])
                        with ci:
                            st.markdown(f"**{item.description}**  ¥{item.amount:.0f}")
                            st.caption(f"加入：{item.added_at[:10]}")
                        with cb1:
                            if st.button("买", key=f"cd_buy_{i}"):
                                item.status = "confirmed"
                                st.rerun()
                        with cb2:
                            if st.button("不买", key=f"cd_skip_{i}"):
                                item.status = "abandoned"
                                st.rerun()
                    st.markdown("---")

            if done:
                with st.expander(f"已处理（{len(done)}）"):
                    for item in done:
                        icon = "✅ 买了" if item.status == "confirmed" else "放弃"
                        st.caption(f"{icon}  {item.description}  ¥{item.amount:.0f}")

    with right:
        render_zone_chat("cool_down", height=430)


def page_detail_finance():
    back_btn()
    st.markdown("### 💡 理财入门")

    accounts = st.session_state.accounts
    now = datetime.now()
    month_str = f"{now.year}-{now.month:02d}"
    month_exp_total = sum(
        e.amount for e in st.session_state.expenses
        if e.timestamp.startswith(month_str) and not e.is_income
    )
    total_balance = sum(a.balance for a in accounts.values())
    min_reserve = st.session_state.get("min_reserve", 500.0)
    goal_savings_needed = sum(g.remaining for g in st.session_state.goals)
    idle_money = max(0.0, total_balance - month_exp_total - goal_savings_needed)

    left, right = st.columns([1.6, 1.4])

    with left:
        with st.container(height=510):
            c1, c2, c3 = st.columns(3)
            c1.metric("总余额", f"¥{total_balance:,.0f}")
            c2.metric("本月支出", f"¥{month_exp_total:,.0f}")
            c3.metric("预计闲钱", f"¥{idle_money:,.0f}")

            tab_advice, tab_learn, tab_calc = st.tabs(["💰 理财建议", "📚 投资课堂", "🔢 复利计算器"])

            with tab_advice:
                reserve_met = total_balance >= min_reserve

                with st.expander("🔰 第一步：确认保底资金", expanded=not reserve_met):
                    if min_reserve > 0:
                        pct = min(total_balance / min_reserve, 1.0)
                        st.progress(pct, text=f"¥{total_balance:,.0f} / ¥{min_reserve:,.0f}（{pct*100:.0f}%）")
                        if reserve_met:
                            st.success("✅ 保底资金已达标！可以开始考虑理财了。")
                        else:
                            st.warning(
                                f"保底资金目标 ¥{min_reserve:,.0f}，还差 ¥{min_reserve - total_balance:,.0f}。"
                            )
                    else:
                        st.info("在资金预警页设置保底资金目标。")

                with st.expander("💰 第二步：货币基金存闲钱", expanded=reserve_met):
                    st.markdown("**货币基金对比（参考）**")
                    data = {
                        "产品": ["招行朝朝宝", "余额宝（蚂蚁）", "零钱通（微信）", "工行活钱管家"],
                        "年化参考": ["约 2.0-2.5%", "约 1.6-1.9%", "约 1.5-1.8%", "约 1.8-2.2%"],
                        "流动性": ["T+0 随取随用", "T+0 随取随用", "T+0 随取随用", "T+0 随取随用"],
                        "特点": ["招行用户首选", "支付宝生态", "微信支付生态", "工行用户方便"],
                    }
                    st.dataframe(pd.DataFrame(data), hide_index=True, use_container_width=True)
                    st.caption("利率随市场波动，仅供参考，不构成投资建议。")
                    st.markdown("**平台直达：**")
                    lc1, lc2, lc3, lc4 = st.columns(4)
                    lc1.link_button("招行朝朝宝", "https://www.cmbchina.com/")
                    lc2.link_button("余额宝", "https://www.alipay.com/")
                    lc3.link_button("零钱通", "https://pay.weixin.qq.com/")
                    lc4.link_button("活钱管家", "https://www.icbc.com.cn/")

                with st.expander("📊 第三步：基金定投入门", expanded=False):
                    st.markdown(
                        "**适合人群：** 保底资金已存够 + 每月有固定结余（建议 ≥ ¥200/月）\n\n"
                        "**操作步骤：**\n"
                        "1. 在招行 APP / 支付宝 开通基金账户（免费）\n"
                        "2. 选择宽基指数基金（如**沪深300**、**中证500**）\n"
                        "3. 设置每月固定金额自动定投（建议每月同一天）\n"
                        "4. 坚持3年以上，平滑市场波动\n\n"
                        "**小花猫建议：** 先从 ¥100-200/月 开始，感受节奏，不要因为短期亏损就中断。\n\n"
                        "**投资有风险，以上仅供参考，不构成投资建议。**"
                    )
                    st.markdown("**开始定投：**")
                    fc1, fc2, fc3 = st.columns(3)
                    fc1.link_button("招商银行APP", "https://www.cmbchina.com/")
                    fc2.link_button("支付宝基金", "https://www.alipay.com/")
                    fc3.link_button("天天基金网", "https://www.1234567.com.cn/")

                if idle_money >= 500:
                    st.info(f"你大约有 **¥{idle_money:,.0f}** 的闲钱。建议先存货币基金，等每月有稳定结余后再考虑定投。")

            with tab_learn:
                st.markdown("##### 大学生必懂的 6 个理财概念")
                st.caption("点击「问小花猫」可以深入聊，点「了解更多」跳转官方资料～")
                for i in range(0, len(FINANCE_CONCEPTS), 2):
                    pair = FINANCE_CONCEPTS[i:i+2]
                    cols = st.columns(2)
                    for col, concept in zip(cols, pair):
                        with col:
                            with st.container(border=True):
                                st.markdown(f"**{concept['emoji']} {concept['title']}**")
                                st.caption(concept["short"])
                                with st.expander("展开详情"):
                                    st.markdown(concept["detail"])
                                btn_col, link_col = st.columns(2)
                                with btn_col:
                                    if st.button(
                                        "问小花猫",
                                        key=f"concept_{concept['title']}",
                                        use_container_width=True,
                                    ):
                                        q = f"用大学生能懂的语言解释一下「{concept['title']}」，结合我的实际财务情况给个建议。"
                                        with st.spinner("小花猫想了想..."):
                                            zone_chat(q, "finance")
                                        st.rerun()
                                with link_col:
                                    url = FINANCE_CONCEPT_LINKS.get(concept["title"], "https://www.cmbchina.com/")
                                    st.link_button("了解更多 →", url, use_container_width=True)

            with tab_calc:
                st.markdown("##### 🔢 复利模拟计算器")
                st.caption("看看坚持定投能积累多少钱（仅供参考，不代表实际收益）")

                ca, cb, cc = st.columns(3)
                with ca:
                    monthly_invest = st.number_input("每月存入（元）", min_value=10.0, max_value=10000.0, value=200.0, step=50.0, key="calc_monthly")
                with cb:
                    invest_years = st.slider("坚持年数", 1, 30, 5, key="calc_years")
                with cc:
                    annual_rate = st.number_input("年化收益率（%）", min_value=0.0, max_value=20.0, value=3.0, step=0.5, key="calc_rate")

                fv, invested, earned = _compound_calc(monthly_invest, invest_years, annual_rate)
                ratio = earned / invested * 100 if invested > 0 else 0

                r1, r2, r3 = st.columns(3)
                r1.metric("最终积累", f"¥{fv:,.0f}")
                r2.metric("累计投入", f"¥{invested:,.0f}")
                r3.metric("利息收益", f"¥{earned:,.0f}", delta=f"+{ratio:.1f}%")

                months_total = invest_years * 12
                months_x = list(range(0, months_total + 1))
                r_monthly = annual_rate / 100 / 12
                if r_monthly > 0:
                    values_calc = [monthly_invest * ((1 + r_monthly) ** m - 1) / r_monthly for m in months_x]
                else:
                    values_calc = [monthly_invest * m for m in months_x]
                invest_line = [monthly_invest * m for m in months_x]

                fig_calc = go.Figure()
                fig_calc.add_trace(go.Scatter(
                    x=[f"第{m//12}年{m%12}月" if m % 12 == 0 else "" for m in months_x],
                    y=values_calc, name="含收益积累", fill="tozeroy",
                    line=dict(color="#FF6B6B", width=2),
                    hovertemplate="第%{pointNumber}个月: ¥%{y:,.0f}<extra>含收益</extra>",
                ))
                fig_calc.add_trace(go.Scatter(
                    x=[f"第{m//12}年{m%12}月" if m % 12 == 0 else "" for m in months_x],
                    y=invest_line, name="纯本金",
                    line=dict(color="#aaa", width=1.5, dash="dash"),
                    hovertemplate="第%{pointNumber}个月: ¥%{y:,.0f}<extra>本金</extra>",
                ))
                fig_calc.update_layout(
                    margin=dict(t=10, b=30, l=10, r=10), height=200,
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=-0.3),
                    yaxis_title="积累金额（元）", showlegend=True,
                )
                st.plotly_chart(fig_calc, width='stretch', key="finance_calc_chart")
                st.caption("⚠️ 仅为数学模拟，实际收益因产品和市场而异，不构成投资建议。")

                if st.button("让小花猫解读这个结果", key="btn_calc_explain", use_container_width=True, type="primary"):
                    q = (f"我打算每月存 ¥{monthly_invest:.0f}，坚持 {invest_years} 年，"
                         f"按年化 {annual_rate}% 计算，最终能积累约 ¥{fv:,.0f}，"
                         f"其中本金 ¥{invested:,.0f}，收益 ¥{earned:,.0f}。"
                         f"结合我的财务状况，你觉得这个计划可行吗？有什么建议？")
                    with st.spinner("小花猫想了想..."):
                        zone_chat(q, "finance")
                    st.rerun()

    with right:
        render_zone_chat("finance", height=430)


def page_detail_alert():
    back_btn()
    st.markdown("### 🔔 资金预警")

    accounts = st.session_state.accounts
    total_balance = sum(a.balance for a in accounts.values())

    left, right = st.columns([1.5, 1.5])

    with left:
        with st.container(height=510):
            # ── 结余概览 ────────────────────────────────────────────────────
            st.markdown("#### 💰 结余概览")
            monthly_data: dict = {}
            for e in st.session_state.expenses:
                m = e.timestamp[:7]
                if m not in monthly_data:
                    monthly_data[m] = {"income": 0.0, "expense": 0.0}
                if e.is_income:
                    monthly_data[m]["income"] += e.amount
                else:
                    monthly_data[m]["expense"] += e.amount

            now_month = datetime.now().strftime("%Y-%m")
            cur = monthly_data.get(now_month, {"income": 0.0, "expense": 0.0})
            net = cur["income"] - cur["expense"]
            save_rate = net / cur["income"] * 100 if cur["income"] > 0 else 0.0

            ma, mb = st.columns(2)
            ma.metric("本月净余", f"¥{net:+,.0f}")
            mb.metric("储蓄率", f"{save_rate:.1f}%")

            months_s = sorted(monthly_data.keys())
            if months_s:
                nets = [monthly_data[m]["income"] - monthly_data[m]["expense"] for m in months_s]
                colors_bar = ["#27ae60" if n >= 0 else "#e74c3c" for n in nets]
                fig_net = go.Figure(go.Bar(
                    x=months_s, y=nets, marker_color=colors_bar,
                    hovertemplate="%{x}: ¥%{y:+,.0f}<extra></extra>",
                ))
                fig_net.add_hline(y=0, line_color="#eee", line_width=1)
                fig_net.update_layout(
                    height=180, margin=dict(t=10, b=20, l=10, r=10),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                )
                st.plotly_chart(fig_net, width='stretch', key="alert_net_chart")

                if len(months_s) >= 2:
                    prev_net = monthly_data[months_s[-2]]["income"] - monthly_data[months_s[-2]]["expense"]
                    diff = net - prev_net
                    if diff > 0:
                        st.success(f"👏 本月结余比上月多 ¥{diff:.0f}，继续！")
                    elif diff < 0:
                        st.warning(f"本月结余比上月少 ¥{abs(diff):.0f}，注意控支出～")
                    else:
                        st.info("本月结余与上月持平。")

            st.markdown("---")

            # ── 今日预算 ────────────────────────────────────────────────────
            st.markdown("#### 📅 今日预算")
            auto_b = accounts["survival"].monthly_income / 30 if accounts["survival"].monthly_income > 0 else 0
            st.caption(f"自动值：¥{auto_b:.0f}/天（基石月收入÷30），设为0则使用自动值")
            nb_col, ns_col = st.columns([2, 1])
            with nb_col:
                new_daily = st.number_input(
                    "今日预算", min_value=0.0,
                    value=float(st.session_state.daily_budget),
                    step=5.0, key="alert_daily",
                    label_visibility="collapsed",
                )
            with ns_col:
                if st.button("保存", key="save_daily_alert"):
                    st.session_state.daily_budget = new_daily
                    st.rerun()

            daily_eff = _effective_daily_budget()
            if daily_eff > 0:
                day_str = datetime.now().strftime("%Y-%m-%d")
                today_spent_val = sum(
                    e.amount for e in st.session_state.expenses
                    if e.timestamp.startswith(day_str) and not e.is_income
                )
                pct_d = min(today_spent_val / daily_eff, 1.0)
                color_d = "#27ae60" if pct_d < 0.85 else "#e74c3c"
                st.markdown(
                    f"<span style='color:{color_d}'>今日已花 ¥{today_spent_val:.0f} / ¥{daily_eff:.0f}</span>",
                    unsafe_allow_html=True,
                )
                st.progress(pct_d)

            st.markdown("---")

            # ── 最低资金阈值 ─────────────────────────────────────────────────
            st.markdown("#### 🔐 最低资金阈值")
            min_r = st.session_state.get("min_reserve", 500.0)
            pct_r = min(total_balance / min_r, 1.0) if min_r > 0 else 1.0
            st.progress(pct_r, text=f"¥{total_balance:,.0f} / ¥{min_r:,.0f}")
            nr_col, ns2_col = st.columns([2, 1])
            with nr_col:
                new_reserve = st.number_input(
                    "最低阈值", min_value=0.0, value=float(min_r),
                    step=100.0, key="alert_reserve",
                    label_visibility="collapsed",
                )
            with ns2_col:
                if st.button("保存", key="save_reserve_alert"):
                    st.session_state.min_reserve = new_reserve
                    st.rerun()
            if total_balance < min_r:
                st.warning(f"⚠️ 余额低于阈值，还差 ¥{min_r - total_balance:.0f}！")
            else:
                st.caption("✅ 余额高于阈值，财务安全")

    with right:
        render_zone_chat("alert", height=430)


# ─── Router ───────────────────────────────────────────────────────────────────

api_key = get_api_key()
if not api_key or api_key == "your-api-key-here":
    st.error("请先在 `.streamlit/secrets.toml` 中填入你的 API Key。")
    st.code('SILICONFLOW_API_KEY = "sk-xxxxxxxxxxxxxxxx"', language="toml")
    st.stop()

page = st.session_state.get("current_page", "landing")

if page == "landing":
    page_landing()
elif page == "main":
    page_main()
elif page == "bill_upload":
    page_bill_upload()
elif page == "detail_accounts":
    page_detail_accounts()
elif page == "detail_spending":
    page_detail_spending()
elif page == "detail_goals":
    page_detail_goals()
elif page == "detail_cool_down":
    page_detail_cool_down()
elif page == "detail_finance":
    page_detail_finance()
elif page == "detail_alert":
    page_detail_alert()
else:
    page_landing()
