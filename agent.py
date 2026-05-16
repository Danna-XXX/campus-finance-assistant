import json
import uuid
from datetime import datetime

import streamlit as st
from openai import OpenAI

from config import SILICONFLOW_BASE_URL, MODEL, get_api_key
from models import Account, Expense, Goal, CoolDownItem, get_financial_snapshot
from prompts import build_system_prompt


def get_client() -> OpenAI:
    return OpenAI(api_key=get_api_key(), base_url=SILICONFLOW_BASE_URL)


def _call_llm(messages: list) -> str:
    client = get_client()
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({
            "message": f"小花猫暂时不在线喵...({e})",
            "action": {"type": "none", "data": {}},
        })


def _parse_response(raw: str) -> tuple[str, dict]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except Exception:
                return "小花猫理解不了你说的，再说一遍？", {"type": "none", "data": {}}
        else:
            return "小花猫理解不了你说的，再说一遍？", {"type": "none", "data": {}}
    return parsed.get("message", ""), parsed.get("action", {"type": "none", "data": {}})


def chat(user_input: str) -> str:
    snapshot = get_financial_snapshot()
    system_prompt = build_system_prompt(
        snapshot=snapshot,
        onboarding_done=st.session_state.onboarding_done,
        onboarding_step=st.session_state.onboarding_step,
        persona_style=st.session_state.get("persona_style", "毒舌好友"),
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages += st.session_state.messages[-20:]
    messages.append({"role": "user", "content": user_input})

    raw = _call_llm(messages)
    message, action = _parse_response(raw)
    apply_action(action)

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": message})
    return message


def zone_chat(user_input: str, zone: str) -> str:
    snapshot = get_financial_snapshot()
    system_prompt = build_system_prompt(
        snapshot=snapshot,
        onboarding_done=True,
        zone=zone,
        persona_style=st.session_state.get("persona_style", "毒舌好友"),
    )
    zone_msgs = st.session_state.zone_messages.get(zone, [])
    messages = [{"role": "system", "content": system_prompt}]
    messages += zone_msgs[-10:]
    messages.append({"role": "user", "content": user_input})

    raw = _call_llm(messages)
    message, action = _parse_response(raw)
    apply_action(action)

    if zone not in st.session_state.zone_messages:
        st.session_state.zone_messages[zone] = []
    st.session_state.zone_messages[zone].append({"role": "user", "content": user_input})
    st.session_state.zone_messages[zone].append({"role": "assistant", "content": message})
    return message


def apply_action(action: dict):
    action_type = action.get("type", "none")
    data = action.get("data", {})
    now = datetime.now().isoformat()[:16]
    accounts = st.session_state.accounts

    if action_type == "record_expense":
        amount = float(data.get("amount", 0))
        account_id = data.get("account", "survival")
        category = data.get("category", "其他")
        description = data.get("description", "")
        if account_id in accounts:
            accounts[account_id].balance -= amount
        st.session_state.expenses.append(Expense(
            timestamp=now, amount=amount, category=category,
            account=account_id, description=description, is_income=False,
        ))

    elif action_type == "record_income":
        amount = float(data.get("amount", 0))
        account_id = data.get("account", "independence")
        description = data.get("description", "")
        if account_id in accounts:
            accounts[account_id].balance += amount
        st.session_state.expenses.append(Expense(
            timestamp=now, amount=amount, category="收入",
            account=account_id, description=description, is_income=True,
        ))

    elif action_type == "update_account":
        account_id = data.get("account_id", "")
        if account_id in accounts:
            acc = accounts[account_id]
            if "balance" in data:
                acc.balance = float(data["balance"])
            if "monthly_income" in data:
                acc.monthly_income = float(data["monthly_income"])
            if "income_type" in data:
                acc.income_type = data["income_type"]

    elif action_type == "set_goal":
        st.session_state.goals.append(Goal(
            id=str(uuid.uuid4())[:8],
            name=data.get("name", "未命名目标"),
            target=float(data.get("target", 0)),
            saved=float(data.get("saved", 0)),
            months=int(data.get("months", 0)),
            source_account=data.get("source_account", "independence"),
            goal_type=data.get("goal_type", "short"),
        ))

    elif action_type == "update_goal_progress":
        goal_id = data.get("goal_id", "")
        add_amount = float(data.get("add_amount", 0))
        for g in st.session_state.goals:
            if g.id == goal_id:
                g.saved = min(g.target, g.saved + add_amount)
                break

    elif action_type == "set_budget":
        category = data.get("category", "")
        limit = float(data.get("limit", 0))
        if category:
            st.session_state.budget[category] = limit

    elif action_type == "add_cool_down":
        st.session_state.cool_down.append(CoolDownItem(
            description=data.get("description", ""),
            amount=float(data.get("amount", 0)),
        ))

    elif action_type == "set_daily_budget":
        amount = float(data.get("amount", 0))
        if amount > 0:
            st.session_state.daily_budget = amount

    elif action_type == "onboarding_complete":
        st.session_state.onboarding_done = True
        st.session_state.onboarding_step = 0

    if not st.session_state.onboarding_done and action_type not in ("none", "onboarding_complete"):
        st.session_state.onboarding_step = min(st.session_state.onboarding_step + 1, 4)
