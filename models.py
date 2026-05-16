from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
import streamlit as st


EXPENSE_CATEGORIES = ["一日三餐", "偶尔小资", "日常出行", "娱乐", "学习", "日用", "家人转账", "朋友转账", "房租水电", "快递物流", "其他"]


@dataclass
class Account:
    id: str
    name: str
    emoji: str
    balance: float
    monthly_income: float = 0.0
    income_type: Literal["fixed", "irregular", "one_time", "none"] = "none"
    subtitle: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "balance": round(self.balance, 2),
            "monthly_income": self.monthly_income,
            "income_type": self.income_type,
        }


@dataclass
class Goal:
    id: str
    name: str
    target: float
    saved: float = 0.0
    months: int = 0
    source_account: str = "independence"
    goal_type: str = "short"
    priority: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat()[:10])

    @property
    def progress_pct(self) -> float:
        if self.target <= 0:
            return 0.0
        return min(100.0, self.saved / self.target * 100)

    @property
    def remaining(self) -> float:
        return max(0.0, self.target - self.saved)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "target": self.target,
            "saved": round(self.saved, 2),
            "months": self.months,
            "source_account": self.source_account,
            "goal_type": self.goal_type,
            "created_at": self.created_at,
            "progress_pct": round(self.progress_pct, 1),
            "remaining": round(self.remaining, 2),
        }


@dataclass
class Expense:
    timestamp: str
    amount: float
    category: str
    account: str
    description: str
    is_income: bool = False

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "amount": self.amount,
            "category": self.category,
            "account": self.account,
            "description": self.description,
            "is_income": self.is_income,
        }


@dataclass
class CoolDownItem:
    description: str
    amount: float
    added_at: str = field(default_factory=lambda: datetime.now().isoformat()[:16])
    status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "amount": self.amount,
            "added_at": self.added_at,
            "status": self.status,
        }


@dataclass
class Challenge:
    id: str
    name: str
    days: int
    start_date: str = field(default_factory=lambda: datetime.now().isoformat()[:10])
    checkins: list = field(default_factory=list)
    status: str = "active"

    @property
    def completed_days(self) -> int:
        return len(self.checkins)

    @property
    def progress_pct(self) -> float:
        if self.days <= 0:
            return 0.0
        return min(100.0, self.completed_days / self.days * 100)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "days": self.days,
            "start_date": self.start_date,
            "checkins": self.checkins,
            "status": self.status,
            "completed_days": self.completed_days,
            "progress_pct": round(self.progress_pct, 1),
        }


DEFAULT_ACCOUNTS = {
    "survival": Account(
        id="survival", name="基石账户", emoji="🏠",
        balance=0.0, monthly_income=0.0, income_type="fixed",
        subtitle="父母给的生活费",
    ),
    "independence": Account(
        id="independence", name="自给账户", emoji="💪",
        balance=0.0, monthly_income=0.0, income_type="none",
        subtitle="兼职·实习·接单",
    ),
    "achievement": Account(
        id="achievement", name="荣誉账户", emoji="🎓",
        balance=0.0, monthly_income=0.0, income_type="none",
        subtitle="奖学金·竞赛奖金",
    ),
}


def init_session_state():
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.current_page = "landing"
        st.session_state.onboarding_done = False
        st.session_state.onboarding_step = 0
        st.session_state.accounts = {
            k: Account(**v.__dict__) for k, v in DEFAULT_ACCOUNTS.items()
        }
        st.session_state.goals = []
        st.session_state.expenses = []
        st.session_state.budget = {}
        st.session_state.messages = []
        st.session_state.zone_messages = {}
        st.session_state.cool_down = []
        st.session_state.bill_analysis_done = False
        st.session_state.daily_budget = 0.0
        st.session_state.min_reserve = 500.0
        st.session_state.challenges = []
        st.session_state.persona_style = "毒舌好友"


def _effective_daily_budget() -> float:
    if st.session_state.daily_budget > 0:
        return st.session_state.daily_budget
    income = st.session_state.accounts["survival"].monthly_income
    return income / 30 if income > 0 else 0.0


def get_financial_snapshot() -> dict:
    accounts = {k: v.to_dict() for k, v in st.session_state.accounts.items()}
    goals = [g.to_dict() for g in st.session_state.goals]

    now = datetime.now()
    month_str = f"{now.year}-{now.month:02d}"
    month_expenses = [
        e.to_dict() for e in st.session_state.expenses
        if e.timestamp.startswith(month_str) and not e.is_income
    ]

    category_totals: dict[str, float] = {}
    for e in month_expenses:
        category_totals[e["category"]] = category_totals.get(e["category"], 0) + e["amount"]

    budget_remaining = {}
    for cat, limit in st.session_state.budget.items():
        spent = category_totals.get(cat, 0)
        budget_remaining[cat] = round(limit - spent, 2)

    daily_budget = _effective_daily_budget()
    day_str = now.strftime("%Y-%m-%d")
    today_spent = sum(
        e.amount for e in st.session_state.expenses
        if e.timestamp.startswith(day_str) and not e.is_income
    )

    total_balance = sum(a.balance for a in st.session_state.accounts.values())
    min_reserve = st.session_state.get("min_reserve", 500.0)

    return {
        "accounts": accounts,
        "goals": goals,
        "this_month_spent_by_category": {k: round(v, 2) for k, v in category_totals.items()},
        "budget_remaining": budget_remaining,
        "cool_down_list": [c.to_dict() for c in st.session_state.cool_down],
        "daily_budget": round(daily_budget, 2),
        "today_spent": round(today_spent, 2),
        "min_reserve": min_reserve,
        "total_balance": round(total_balance, 2),
    }
