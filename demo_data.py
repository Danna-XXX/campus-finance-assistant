"""
Pre-built demo data for 小花猫 quick-start experience.
load_demo_data() populates session_state with 1+ months of realistic data.
DEMO_BILL_RESULT is a pre-computed bill analysis (instant display, no LLM call needed).
SAMPLE_PREVIEW_ROWS is a curated selection of representative transactions for the preview table.
"""
import uuid
from datetime import datetime, timedelta

import streamlit as st

from models import Account, Expense, Goal, CoolDownItem, Challenge, DEFAULT_ACCOUNTS


# ─── Sample preview rows shown below the "内置示例账单" radio option ────────────

SAMPLE_PREVIEW_ROWS = [
    {"日期": "2025-05-12", "交易类型": "扫码付款", "交易对方": "学校第一食堂", "商品": "午饭", "金额": "¥12.50", "分类": "🍚 一日三餐"},
    {"日期": "2025-06-03", "交易类型": "扫码付款", "交易对方": "瑞幸咖啡", "商品": "生椰拿铁", "金额": "¥19.90", "分类": "🧋 偶尔小资"},
    {"日期": "2025-07-08", "交易类型": "扫码付款", "交易对方": "万达影城", "商品": "电影票", "金额": "¥39.90", "分类": "🎬 娱乐"},
    {"日期": "2025-09-02", "交易类型": "扫码付款", "交易对方": "新华书店", "商品": "微积分教材", "金额": "¥58.00", "分类": "📚 学习"},
    {"日期": "2025-10-15", "交易类型": "转账", "交易对方": "妈妈", "商品": "生活费", "金额": "¥2500.00", "分类": "👨‍👩‍👧 家人转账"},
    {"日期": "2025-11-11", "交易类型": "扫码付款", "交易对方": "天猫超市", "商品": "日用品", "金额": "¥86.50", "分类": "🛒 日用"},
    {"日期": "2025-12-20", "交易类型": "扫码付款", "交易对方": "滴滴出行", "商品": "快车", "金额": "¥18.60", "分类": "🚕 日常出行"},
    {"日期": "2026-02-14", "交易类型": "转账", "交易对方": "顺丰速运", "商品": "快递费", "金额": "¥12.00", "分类": "📦 快递物流"},
]


# ─── Pre-computed bill analysis result (avoids LLM call for demo) ──────────────

DEMO_BILL_RESULT = {
    "time_span": {"months": 12, "start": "2025-05", "end": "2026-04"},
    "headline": "过去一年，你在奶茶咖啡上花了 ¥1,915，比全年所有书本教材加起来还多 2.7 倍！",
    "full_summary": {
        "total_income": 32800.0,
        "total_expense": 16526.0,
        "monthly_avg_expense": 1377.0,
        "category_breakdown": {
            "一日三餐": 9205.0,
            "偶尔小资": 1915.0,
            "娱乐": 1945.0,
            "日用": 1241.0,
            "日常出行": 855.0,
            "学习": 710.0,
            "快递物流": 145.0,
            "其他": 510.0,
        },
        "top_insights": [
            "一日三餐占全年支出的 55.7%，每天平均吃饭花 ¥25.2，是最大支出项",
            "2025年暑假（7-8月）娱乐支出分别达 ¥320/¥280，是平均月份的 3 倍",
            "偶尔小资（奶茶咖啡）全年 ¥1,915，下半年比上半年多花了 ¥230，呈上涨趋势",
        ],
        "summary_text": "总体来看，你的消费结构比较均衡，生活费没有大起大落。但奶茶和暑假娱乐是两个明显的「失控点」，稍加控制每月能多省 ¥100-200 实现更多储蓄。",
    },
    "monthly_breakdown": [
        {"month": "2025-05", "income": 2500.0, "total_expense": 1300.0, "top_category": "一日三餐"},
        {"month": "2025-06", "income": 2500.0, "total_expense": 1386.0, "top_category": "一日三餐"},
        {"month": "2025-07", "income": 3000.0, "total_expense": 1500.0, "top_category": "一日三餐"},
        {"month": "2025-08", "income": 2500.0, "total_expense": 1450.0, "top_category": "一日三餐"},
        {"month": "2025-09", "income": 3300.0, "total_expense": 1442.0, "top_category": "一日三餐"},
        {"month": "2025-10", "income": 2500.0, "total_expense": 1375.0, "top_category": "一日三餐"},
        {"month": "2025-11", "income": 2500.0, "total_expense": 1325.0, "top_category": "一日三餐"},
        {"month": "2025-12", "income": 2500.0, "total_expense": 1405.0, "top_category": "一日三餐"},
        {"month": "2026-01", "income": 3500.0, "total_expense": 1260.0, "top_category": "一日三餐"},
        {"month": "2026-02", "income": 2500.0, "total_expense": 1345.0, "top_category": "一日三餐"},
        {"month": "2026-03", "income": 3000.0, "total_expense": 1351.0, "top_category": "一日三餐"},
        {"month": "2026-04", "income": 2500.0, "total_expense": 1387.0, "top_category": "一日三餐"},
    ],
    "trends": {
        "increasing": ["偶尔小资"],
        "decreasing": ["学习"],
        "most_stable": "一日三餐",
        "trend_text": "奶茶咖啡消费持续走高，下半年比上半年多花了 ¥230，要注意啦。一日三餐是最稳定的，每月在 ¥650-¥850 之间浮动，说明饮食习惯比较规律。",
    },
    "persona": {
        "type": "享乐均衡型",
        "emoji": "🎭",
        "strengths": [
            "生活费管理整体稳定，全年月支出波动不超过 ¥250",
            "学习投入有规律性，开学季会主动购置教材和工具书",
        ],
        "blindspots": [
            "奶茶咖啡消费逐月上涨，已超过全年学习支出的 2.7 倍，情绪消费明显",
            "假期（暑假/国庆）娱乐支出明显失控，缺乏淡旺季预算意识",
        ],
        "tips": [
            "给奶茶设个月上限 ¥120，超了就在家用咖啡机整（更香，更省）",
            "假期前提前设定娱乐月预算，把娱乐钱单独存出来，花完就停",
            "每天有意识地少花一点，积累的正反馈很上头的",
        ],
    },
    "suggested_accounts": {
        "survival": {"monthly_income": 2500.0, "note": "检测到每月固定¥2500转账收入，推测为家庭生活费"},
        "independence": {"balance": 480.0, "monthly_income": 500.0, "income_type": "irregular", "note": "检测到多笔不定期小额转账收入，推测为兼职/家教收入"},
        "achievement": {"balance": 0.0, "note": "未检测到明显奖学金或竞赛奖金记录"},
    },
    "monthly_agg": {
        "2025-05": {"income": 2500.0, "expense": {"一日三餐": 780.0, "偶尔小资": 120.0, "日常出行": 65.0, "娱乐": 85.0, "学习": 110.0, "日用": 95.0, "其他": 45.0}, "total_expense": 1300.0},
        "2025-06": {"income": 2500.0, "expense": {"一日三餐": 820.0, "偶尔小资": 145.0, "日常出行": 58.0, "娱乐": 210.0, "学习": 35.0, "日用": 88.0, "其他": 30.0}, "total_expense": 1386.0},
        "2025-07": {"income": 3000.0, "expense": {"一日三餐": 650.0, "偶尔小资": 220.0, "日常出行": 85.0, "娱乐": 320.0, "日用": 120.0, "快递物流": 65.0, "其他": 40.0}, "total_expense": 1500.0},
        "2025-08": {"income": 2500.0, "expense": {"一日三餐": 680.0, "偶尔小资": 195.0, "日常出行": 75.0, "娱乐": 280.0, "日用": 105.0, "快递物流": 80.0, "其他": 35.0}, "total_expense": 1450.0},
        "2025-09": {"income": 3300.0, "expense": {"一日三餐": 810.0, "偶尔小资": 135.0, "日常出行": 62.0, "娱乐": 90.0, "学习": 180.0, "日用": 110.0, "其他": 55.0}, "total_expense": 1442.0},
        "2025-10": {"income": 2500.0, "expense": {"一日三餐": 795.0, "偶尔小资": 150.0, "日常出行": 70.0, "娱乐": 180.0, "学习": 45.0, "日用": 95.0, "其他": 40.0}, "total_expense": 1375.0},
        "2025-11": {"income": 2500.0, "expense": {"一日三餐": 830.0, "偶尔小资": 165.0, "日常出行": 60.0, "娱乐": 75.0, "学习": 60.0, "日用": 100.0, "其他": 35.0}, "total_expense": 1325.0},
        "2025-12": {"income": 2500.0, "expense": {"一日三餐": 850.0, "偶尔小资": 160.0, "日常出行": 65.0, "娱乐": 120.0, "学习": 30.0, "日用": 130.0, "其他": 50.0}, "total_expense": 1405.0},
        "2026-01": {"income": 3500.0, "expense": {"一日三餐": 580.0, "偶尔小资": 130.0, "日常出行": 120.0, "娱乐": 280.0, "日用": 90.0, "其他": 60.0}, "total_expense": 1260.0},
        "2026-02": {"income": 2500.0, "expense": {"一日三餐": 750.0, "偶尔小资": 140.0, "日常出行": 55.0, "娱乐": 100.0, "学习": 150.0, "日用": 105.0, "其他": 45.0}, "total_expense": 1345.0},
        "2026-03": {"income": 3000.0, "expense": {"一日三餐": 820.0, "偶尔小资": 175.0, "日常出行": 68.0, "娱乐": 95.0, "学习": 55.0, "日用": 98.0, "其他": 40.0}, "total_expense": 1351.0},
        "2026-04": {"income": 2500.0, "expense": {"一日三餐": 840.0, "偶尔小资": 180.0, "日常出行": 72.0, "娱乐": 110.0, "学习": 45.0, "日用": 105.0, "其他": 35.0}, "total_expense": 1387.0},
    },
}


# ─── Demo session state loader ─────────────────────────────────────────────────

def load_demo_data():
    """Populate session_state with ~1.5 months of realistic mock data."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    prev_month = (now.replace(day=1) - timedelta(days=1))
    prev_month_str = prev_month.strftime("%Y-%m")

    # Accounts
    st.session_state.accounts = {
        k: Account(**v.__dict__) for k, v in DEFAULT_ACCOUNTS.items()
    }
    st.session_state.accounts["survival"].balance = 1600.0
    st.session_state.accounts["survival"].monthly_income = 2000.0
    st.session_state.accounts["survival"].income_type = "fixed"
    st.session_state.accounts["independence"].balance = 480.0
    st.session_state.accounts["independence"].monthly_income = 500.0
    st.session_state.accounts["independence"].income_type = "irregular"
    st.session_state.accounts["achievement"].balance = 3000.0
    st.session_state.accounts["achievement"].income_type = "one_time"

    st.session_state.min_reserve = 500.0
    st.session_state.daily_budget = 0.0
    st.session_state.onboarding_done = True
    st.session_state.onboarding_step = 0
    if "persona_style" not in st.session_state:
        st.session_state.persona_style = "毒舌好友"

    # ── Expenses: last month (full month) ─────────────────────────────────────
    pm = prev_month_str
    raw_expenses = [
        # 一日三餐
        (f"{pm}-01 12:20", 12.0, "一日三餐", "survival", "食堂午饭"),
        (f"{pm}-02 18:30", 8.5, "一日三餐", "survival", "食堂晚饭"),
        (f"{pm}-03 19:00", 58.0, "一日三餐", "survival", "烤肉（和同学聚餐）"),
        (f"{pm}-05 12:30", 35.0, "一日三餐", "survival", "外卖（美团）"),
        (f"{pm}-07 12:10", 11.0, "一日三餐", "survival", "食堂午饭"),
        (f"{pm}-08 18:30", 9.0, "一日三餐", "survival", "食堂晚饭"),
        (f"{pm}-10 12:30", 42.0, "一日三餐", "survival", "外卖（饿了么）"),
        (f"{pm}-11 12:20", 12.5, "一日三餐", "survival", "食堂午饭"),
        (f"{pm}-13 08:00", 8.0, "一日三餐", "survival", "早餐（沙县小吃）"),
        (f"{pm}-14 18:30", 10.0, "一日三餐", "survival", "食堂晚饭"),
        (f"{pm}-16 12:30", 38.0, "一日三餐", "survival", "外卖（美团）"),
        (f"{pm}-18 12:20", 13.0, "一日三餐", "survival", "食堂午饭"),
        (f"{pm}-19 08:30", 7.5, "一日三餐", "survival", "早餐（煎饼）"),
        (f"{pm}-21 12:30", 35.5, "一日三餐", "survival", "外卖（饿了么）"),
        (f"{pm}-22 18:30", 9.5, "一日三餐", "survival", "食堂晚饭"),
        (f"{pm}-25 12:20", 11.5, "一日三餐", "survival", "食堂午饭"),
        (f"{pm}-27 12:30", 40.0, "一日三餐", "survival", "外卖（美团）"),
        (f"{pm}-28 18:30", 9.0, "一日三餐", "survival", "食堂晚饭"),
        (f"{pm}-30 12:00", 12.0, "一日三餐", "survival", "食堂午饭"),
        # 偶尔小资
        (f"{pm}-02 15:45", 19.9, "偶尔小资", "survival", "瑞幸咖啡 生椰拿铁"),
        (f"{pm}-09 16:00", 32.0, "偶尔小资", "survival", "喜茶 多肉葡萄"),
        (f"{pm}-17 14:30", 16.8, "偶尔小资", "survival", "瑞幸咖啡 美式"),
        (f"{pm}-25 15:00", 28.0, "偶尔小资", "survival", "霸王茶姬 伯牙绝弦"),
        # 日常出行
        (f"{pm}-04 09:00", 22.6, "日常出行", "survival", "滴滴快车"),
        (f"{pm}-06 08:30", 4.0, "日常出行", "survival", "地铁"),
        (f"{pm}-20 08:30", 4.0, "日常出行", "survival", "地铁"),
        (f"{pm}-24 18:00", 18.0, "日常出行", "survival", "滴滴快车"),
        # 娱乐
        (f"{pm}-05 19:30", 45.0, "娱乐", "independence", "电影票（万达影城）"),
        (f"{pm}-15 20:00", 25.0, "娱乐", "survival", "bilibili大会员 + 番剧"),
        # 学习
        (f"{pm}-01 10:00", 15.0, "学习", "survival", "打印论文"),
        (f"{pm}-22 14:00", 39.0, "学习", "achievement", "参考书（考研数学）"),
        # 日用
        (f"{pm}-12 10:30", 67.5, "日用", "survival", "超市（物美）日用品"),
        (f"{pm}-23 21:00", 28.5, "日用", "survival", "全家便利店"),
    ]

    # ── Expenses: this month days 1 to yesterday ──────────────────────────────
    cur_month_str = now.strftime("%Y-%m")
    cm = cur_month_str
    day = now.day

    this_month_raw = []
    if day >= 2:
        this_month_raw += [
            (f"{cm}-01 12:20", 11.0, "一日三餐", "survival", "食堂午饭"),
            (f"{cm}-01 08:15", 19.9, "偶尔小资", "survival", "瑞幸咖啡"),
        ]
    if day >= 4:
        this_month_raw += [
            (f"{cm}-03 18:30", 8.5, "一日三餐", "survival", "食堂晚饭"),
            (f"{cm}-04 12:30", 35.0, "一日三餐", "survival", "外卖（美团）"),
        ]
    if day >= 7:
        this_month_raw += [
            (f"{cm}-06 09:00", 22.0, "日常出行", "survival", "滴滴快车"),
            (f"{cm}-07 12:20", 12.0, "一日三餐", "survival", "食堂午饭"),
        ]
    if day >= 10:
        this_month_raw += [
            (f"{cm}-09 16:00", 29.0, "偶尔小资", "survival", "喜茶"),
            (f"{cm}-10 19:30", 49.0, "娱乐", "independence", "电影票"),
        ]
    if day >= 13:
        this_month_raw += [
            (f"{cm}-12 10:30", 72.0, "日用", "survival", "超市（永辉）"),
            (f"{cm}-13 12:30", 38.0, "一日三餐", "survival", "外卖（饿了么）"),
        ]
    if day >= 15:
        this_month_raw += [
            (f"{cm}-14 12:20", 11.5, "一日三餐", "survival", "食堂午饭"),
            (f"{cm}-15 20:00", 25.0, "娱乐", "survival", "bilibili会员"),
        ]

    # Today: just one meal, so there's a savings amount visible
    today_raw = [(f"{today} 08:10", 18.0, "一日三餐", "survival", "食堂早饭")]

    all_raw = raw_expenses + this_month_raw + today_raw

    expenses = []
    for item in all_raw:
        ts, amount, category, account, desc = item
        expenses.append(Expense(
            timestamp=ts, amount=amount, category=category,
            account=account, description=desc, is_income=False,
        ))

    # ── Income records (is_income=True) ───────────────────────────────────────
    income_raw = [
        # 基石账户：每月固定生活费
        ("2026-04-01 08:00", 2000.0, "收入", "survival", "生活费（父母转账）"),
        (f"{cm}-01 08:00",   2000.0, "收入", "survival", "生活费（父母转账）"),
        # 自给账户：兼职（周末家教）
        ("2026-04-06 20:00", 300.0, "收入", "independence", "[兼职] 周末家教"),
        ("2026-04-13 20:00", 300.0, "收入", "independence", "[兼职] 周末家教"),
        ("2026-04-20 20:00", 300.0, "收入", "independence", "[兼职] 周末家教"),
        ("2026-04-27 20:00", 300.0, "收入", "independence", "[兼职] 周末家教"),
        (f"{cm}-06 20:00",   300.0, "收入", "independence", "[兼职] 周末家教"),
        (f"{cm}-13 20:00",   300.0, "收入", "independence", "[兼职] 周末家教"),
        # 自给账户：实习薪资
        ("2026-04-25 10:00", 800.0, "收入", "independence", "[实习] 暑期实习工资"),
        # 荣誉账户：奖学金
        ("2026-04-15 10:00", 3000.0, "收入", "achievement", "国家励志奖学金"),
    ]
    for item in income_raw:
        ts, amount, category, account, desc = item
        expenses.append(Expense(
            timestamp=ts, amount=amount, category=category,
            account=account, description=desc, is_income=True,
        ))

    st.session_state.expenses = expenses

    # ── Goals ─────────────────────────────────────────────────────────────────
    st.session_state.goals = [
        Goal(
            id="demo_g1",
            name="毕业旅行基金",
            target=3000.0,
            saved=1200.0,
            months=4,
            source_account="independence",
            goal_type="short",
            created_at="2026-02-01",
        ),
        Goal(
            id="demo_g2",
            name="新款耳机",
            target=799.0,
            saved=799.0,
            months=0,
            source_account="independence",
            goal_type="short",
            created_at="2026-01-15",
        ),
        Goal(
            id="demo_g3",
            name="第一桶金",
            target=10000.0,
            saved=1085.0,
            months=18,
            source_account="survival",
            goal_type="long",
            created_at="2025-09-01",
        ),
    ]

    # ── Cool down items ────────────────────────────────────────────────────────
    t_base = now - timedelta(days=2)
    st.session_state.cool_down = [
        CoolDownItem(
            description="AirPods Pro（第三代）",
            amount=1599.0,
            added_at=(now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
            status="pending",
        ),
        CoolDownItem(
            description="Nintendo Switch OLED",
            amount=2499.0,
            added_at=(now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
            status="pending",
        ),
        CoolDownItem(
            description="运动外套（耐克）",
            amount=389.0,
            added_at=(now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            status="pending",
        ),
    ]

    # ── Challenges ────────────────────────────────────────────────────────────
    st.session_state.challenges = [
        Challenge(
            id="demo_ch1",
            name="21天不点外卖",
            days=21,
            start_date=(now - timedelta(days=8)).strftime("%Y-%m-%d"),
            checkins=[(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7, 0, -1)],
            status="active",
        ),
    ]

    # ── Pre-seeded chat messages ───────────────────────────────────────────────
    st.session_state.messages = [
        {"role": "assistant", "content": (
            "账户已经帮你建好啦 🐱 基石账户 ¥1,600、自给账户 ¥480、荣誉账户 ¥3,000～\n\n"
            "随时告诉我今天花了什么，或者问我「这个东西该不该买」！"
        )},
    ]

    st.session_state.zone_messages = {
        "spending": [
            {"role": "user", "content": "我这个月奶茶花了多少？"},
            {"role": "assistant", "content": (
                "刚帮你算了一下，上个月偶尔小资（奶茶咖啡）合计 ¥96.7，"
                "平均每周 ¥24 左右～\n\n"
                "说实话还好，没到失控的程度。但如果每月能控制在 ¥80 以内，"
                "多省的那 ¥20 一年也是 ¥240，挺可观的～"
            )},
        ],
        "finance": [
            {"role": "user", "content": "我现在适合买基金吗？"},
            {"role": "assistant", "content": (
                "你现在总余额 ¥5,165，保底资金 ¥500 早就达标了——所以理论上可以开始考虑理财了！\n\n"
                "我的建议是这样：先把超出日常支出的闲钱（大概 ¥1,500 左右）"
                "放招行朝朝宝，随取随用，年化约 2%。等这个习惯稳了，"
                "再每月拿 ¥200 做沪深300指数基金定投，荣誉账户的奖学金就先别动它～\n\n"
                "⚠️ 仅供参考，不构成投资建议。"
            )},
        ],
    }

    st.session_state.budget = {}
    st.session_state.bill_analysis_done = False
    st.session_state.current_page = "main"
