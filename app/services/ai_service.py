from datetime import date, timedelta
import json
import re
from typing import Any

from openai import OpenAI
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.attendance import Attendance
from app.models.conversation import Conversation
from app.models.user import User, UserRole


ALLOWED_TABLES: dict[str, set[str]] = {
    "attendance": {"id", "user_id", "date", "status", "notes", "image_path", "created_at"},
    "users": {"id", "name", "email", "role", "team_id", "created_at"},
    "teams": {"id", "name"},
    "conversations": {"id", "user_id", "message", "response", "created_at"},
}
READ_ONLY_SQL_PREFIXES = ("select", "with")
FORBIDDEN_SQL_TERMS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "truncate",
    "create",
    "grant",
    "revoke",
)
MAX_SQL_RESULT_ROWS = 100
# How many prior user/assistant turns to load from DB and send to the planner (chronological).
PLANNER_HISTORY_TURNS = 10
# Max rows passed to the final natural-language formatter (full fidelity within cap).
RESULT_FORMATTER_MAX_ROWS = min(MAX_SQL_RESULT_ROWS, 80)


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    """Parse the first JSON object from an LLM response."""
    candidate = raw_text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("The model did not return a valid JSON object.")
    return json.loads(candidate[start : end + 1])


def _build_agent_planning_prompt(
    user: User,
    message: str,
    conversation_history: list[dict[str, Any]],
) -> str:
    """Build a dynamic planning prompt for intent, action, and SQL generation."""
    # Use chronological order (oldest → newest) so follow-ups and refinements read naturally.
    turns = conversation_history[-PLANNER_HISTORY_TURNS:]
    history_text = "\n".join(
        [f"- User: {item['message']}\n  Assistant: {item['response']}" for item in turns]
    ) or "- No recent messages."
    return f"""
You are an intelligent AI assistant for a sports attendance SaaS.

Current authenticated user context:
- id: {user.id}
- name: {user.name}
- role: {user.role.value}
- team_id: {user.team_id}

Allowed database schema:
- attendance(id, user_id, date, status, notes, image_path, created_at)
- users(id, name, email, role, team_id, created_at)
- teams(id, name)
- conversations(id, user_id, message, response, created_at)

Role access policy:
- player: can access only own records using :current_user_id
- manager: can access only own team using :current_team_id
- admin: can access all data

Rules:
- Understand the user's meaning dynamically. Do not rely on fixed keyword behavior.
- If the question can be answered from current user context (example: "Who am I?"), answer directly.
- If question is unclear, ask a polite clarification question.
- Use SQL only when needed.
- SQL must be read-only SELECT/WITH and use named params.
- Prefer selective column lists (not SELECT * unless needed), apply role scope in WHERE, and add ORDER BY when returning lists so results are stable and complete.
- Do not add a LIMIT yourself unless the user asks for a sample or top-N; the server may cap wide results.
- Never mention SQL, queries, tables, or technical internals in the final user-facing response.
- Keep tone polite, clear, and human.
- Avoid unnecessary clarifying questions when user intent is already clear.
- If user asks "all users details" or equivalent:
  - admin: return all users.
  - manager: return users from own team only (auto-apply team scope).
  - player: return only own profile details.
- If user asks "who are manager" or equivalent, return list of manager users (role = manager), scoped by role policy.
- If user asks "my details" / "who am I", answer directly from current authenticated user context.
- If user asks "today attendance" without target:
  - player: default to own today's attendance.
  - manager/admin: default to team/global summary by role scope without asking extra clarification.
- For entity lookup like "attendance of John" followed by "John chouhan", use conversation context and refine search directly.
- Clarification should be used only when multiple plausible targets remain after best effort resolution.
- Never answer a list query with self-identity text (example: for "who are manager", never reply "You are the manager").

Behavior examples (follow these patterns):
1) User: "Can you provide me complete users details"
   Assistant action: run_sql (not clarify), scoped by role policy.
2) User: "i want all users details" -> run_sql, no repeat clarification.
3) User: "all users" after previous turns -> use context, run_sql directly.
4) User: "who are manager" -> run_sql returning manager users list (scoped).
5) User: "can you Provide me my complete details" -> direct_response from current user context.
6) User: "can you provide me today attendance" -> run_sql with sensible role-based default.
7) User: "i want attendance of John" then "John chouhan" -> use follow-up context and run_sql with refined filter.

Recent conversation:
{history_text}

User message:
{message}

Return valid JSON only:
{{
  "intent": "short intent label",
  "action": "direct_response | clarify | run_sql",
  "response": "required for direct_response/clarify",
  "sql": "required only for run_sql",
  "parameters": {{"current_user_id": {user.id}, "current_team_id": {user.team_id if user.team_id is not None else "null"}}},
  "explanation": "one-line human summary for result formatting"
}}
""".strip()


def _build_result_response_prompt(
    user: User,
    message: str,
    intent: str,
    explanation: str,
    result_data: list[dict[str, Any]],
) -> str:
    """Build prompt to convert DB results into natural response."""
    total = len(result_data)
    rows_for_model = result_data[:RESULT_FORMATTER_MAX_ROWS]
    omitted = total - len(rows_for_model)
    omitted_note = (
        f"\nNote: {omitted} additional rows were omitted here for length; state the total count and offer to narrow the question."
        if omitted > 0
        else ""
    )
    return f"""
You are a helpful assistant. Create a final response for the user.

User context:
- name: {user.name}
- role: {user.role.value}

Intent: {intent}
User question: {message}
Planner explanation: {explanation}
Row count (full result set): {total}
Complete rows for this response (up to {RESULT_FORMATTER_MAX_ROWS}; use every row below — do not invent or drop rows): {rows_for_model}
{omitted_note}

Rules:
- Be polite, concise, and easy to understand.
- Do not mention SQL, database, query execution, or technical internals.
- If row count is 0, apologize politely and suggest what detail the user can provide next.
- If data exists, reflect all rows provided above: for lists, include each entry (name/role/date/status as relevant). Do not summarize away rows the user asked to see in full.
- If many rows were omitted (note above), say how many total and offer to filter.
- End with a brief help offer.
- For list questions, enumerate items from the data instead of generic text.
- For profile/self questions, explicitly include name, role, and team status (if available).
- For attendance questions, include status/date summary in plain language.
""".strip()


def _get_ai_client_and_model(settings: Any) -> tuple[OpenAI | None, str | None]:
    """Return a configured OpenAI-compatible client and model."""
    preferred_provider = settings.ai_provider.lower().strip()
    openai_available = bool(
        settings.openai_api_key and len(settings.openai_api_key) > 10 and settings.openai_api_key != "dummy"
    )
    groq_available = bool(
        settings.groq_api_key and len(settings.groq_api_key) > 10 and settings.groq_api_key != "dummy"
    )

    if preferred_provider == "groq" and groq_available:
        client = OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")
        model = settings.ai_model if settings.ai_model and not settings.ai_model.startswith("gpt-") else "llama-3.3-70b-versatile"
        return client, model
    if preferred_provider == "openai" and openai_available:
        return OpenAI(api_key=settings.openai_api_key), settings.ai_model

    if groq_available:
        client = OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")
        model = settings.ai_model if settings.ai_model and not settings.ai_model.startswith("gpt-") else "llama-3.3-70b-versatile"
        return client, model
    if openai_available:
        return OpenAI(api_key=settings.openai_api_key), settings.ai_model
    return None, None


def _enforce_read_only_sql(sql_query: str) -> str:
    """Validate SQL is read-only and constrained to known schema."""
    normalized = " ".join(sql_query.strip().split())
    lowered = normalized.lower()

    if not lowered.startswith(READ_ONLY_SQL_PREFIXES):
        raise ValueError("Only read-only SELECT/WITH queries are allowed.")
    if ";" in lowered or "--" in lowered or "/*" in lowered or "*/" in lowered:
        raise ValueError("Multiple statements or SQL comments are not allowed.")
    if any(re.search(rf"\b{term}\b", lowered) for term in FORBIDDEN_SQL_TERMS):
        raise ValueError("Write or DDL SQL terms are forbidden.")

    referenced_tables = set(re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", lowered))
    if not referenced_tables:
        raise ValueError("Query must reference at least one table.")
    unknown_tables = referenced_tables - set(ALLOWED_TABLES.keys())
    if unknown_tables:
        raise ValueError(f"Query references unknown tables: {', '.join(sorted(unknown_tables))}")

    for table_name, column_name in re.findall(r"\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\b", lowered):
        if table_name in ALLOWED_TABLES and column_name not in ALLOWED_TABLES[table_name]:
            raise ValueError(f"Column {table_name}.{column_name} is not allowed.")

    if " limit " not in lowered:
        normalized = f"{normalized} LIMIT {MAX_SQL_RESULT_ROWS}"
    return normalized


def _enforce_role_scope(sql_query: str, user: User) -> None:
    """Extra server-side role guard beyond prompt instructions."""
    lowered = sql_query.lower()
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.PLAYER:
        if ":current_user_id" not in lowered:
            raise ValueError("Access policy violation for player scope.")
        return
    if user.role == UserRole.MANAGER:
        if user.team_id is None:
            raise ValueError("Manager account is missing a team assignment.")
        if ":current_team_id" not in lowered:
            raise ValueError("Access policy violation for manager scope.")


def _run_sql_agent(
    db: Session,
    user: User,
    message: str,
    conversation_history: list[dict[str, Any]],
) -> str:
    """Run dynamic planning, optional SQL execution, and natural response generation."""
    get_settings.cache_clear()
    settings = get_settings()
    client, model = _get_ai_client_and_model(settings)
    if not client or not model:
        raise RuntimeError("No AI provider configured for SQL agent.")

    system_message = (
        "You are a strict JSON-only assistant. Return valid JSON and no additional markdown or prose."
    )
    planning_prompt = _build_agent_planning_prompt(user, message, conversation_history)
    llm_response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": planning_prompt},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    content = llm_response.choices[0].message.content if llm_response.choices else ""
    print(f"LLM Response=========================================================>: {content}")
    if not content:
        raise ValueError("Agent planning returned empty output.")

    plan = _parse_json_object(content)
    action = str(plan.get("action", "")).strip()
    intent = str(plan.get("intent", "general_assistance")).strip()
    response_text = str(plan.get("response", "")).strip()

    if action in {"direct_response", "clarify"}:
        if response_text:
            return response_text
        return "I didn't fully understand your request. Could you please rephrase it?"

    if action != "run_sql":
        return "I didn't fully understand your request. Could you please rephrase it?"

    generated_sql = str(plan.get("sql", "")).strip()
    if not generated_sql:
        raise ValueError("SQL action selected without SQL statement.")

    safe_sql = _enforce_read_only_sql(generated_sql)
    _enforce_role_scope(safe_sql, user)

    user_parameters = plan.get("parameters") or {}
    if not isinstance(user_parameters, dict):
        user_parameters = {}
    # Server-owned bind names; never allow the model to override scope parameters.
    safe_params: dict[str, Any] = {
        **{k: v for k, v in user_parameters.items() if isinstance(k, str) and k not in {"current_user_id", "current_team_id"}},
        "current_user_id": user.id,
        "current_team_id": user.team_id,
    }

    result_rows = db.execute(text(safe_sql), safe_params).mappings().all()
    result_data = [dict(row) for row in result_rows]

    result_prompt = _build_result_response_prompt(
        user=user,
        message=message,
        intent=intent,
        explanation=str(plan.get("explanation", "Here is what I found.")),
        result_data=result_data,
    )
    row_count = len(result_data)
    result_max_tokens = 420 if row_count <= 15 else (900 if row_count <= 50 else 1200)
    result_response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a polite, non-technical assistant."},
            {"role": "user", "content": result_prompt},
        ],
        temperature=0.3,
        max_tokens=result_max_tokens,
    )
    final_text = result_response.choices[0].message.content if result_response.choices else ""
    if final_text and final_text.strip():
        return final_text.strip()
    return "I found the information you asked for. Let me know if you would like more details."


def _build_prompt(rows: list[dict[str, Any]], days: int) -> str:
    return (
        "You are an attendance analyst. Provide concise insights in 3 bullet points.\n"
        f"Analyze attendance trends over the last {days} days.\n"
        "Include potential risks and one action recommendation.\n"
        f"Data: {rows}"
    )


def _fetch_attendance_window(db: Session, days: int, team_id: int | None = None) -> list[dict[str, Any]]:
    since = date.today() - timedelta(days=days)
    query = (
        select(Attendance.date, Attendance.status, User.name)
        .join(User, User.id == Attendance.user_id)
        .where(Attendance.date >= since)
    )
    if team_id:
        query = query.where(User.team_id == team_id)
    result = db.execute(query).all()
    return [{"date": str(r.date), "status": r.status.value, "user": r.name} for r in result]


def generate_insights(db: Session, days: int = 14, team_id: int | None = None) -> str:
    # Refresh cached settings so updated .env values are picked up after reloads.
    get_settings.cache_clear()
    settings = get_settings()
    rows = _fetch_attendance_window(db, days=days, team_id=team_id)
    if not rows:
        return "No attendance data available for the selected period."

    preferred_provider = settings.ai_provider.lower().strip()
    use_openai = preferred_provider == "openai" and bool(settings.openai_api_key)
    use_groq = preferred_provider == "groq" and bool(settings.groq_api_key)

    # Auto fallback to available key if provider is misconfigured.
    if not use_openai and not use_groq:
        if settings.openai_api_key:
            use_openai = True
        elif settings.groq_api_key:
            use_groq = True

    if use_groq:
        try:
            client = OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1")
            # Groq is most reliable with Chat Completions-style requests.
            groq_model = settings.ai_model
            if not groq_model or groq_model.startswith("gpt-"):
                groq_model = "llama-3.3-70b-versatile"
            response = client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": "You are an attendance analyst."},
                    {"role": "user", "content": _build_prompt(rows, days)},
                ],
                temperature=0.3,
                max_tokens=220,
            )
            content = response.choices[0].message.content if response.choices else ""
            if content:
                return content.strip()
            return "AI insights were generated but returned empty output."
        except Exception:
            return "Groq insights failed. Verify GROQ_API_KEY and AI_MODEL for Groq."

    # Fallback deterministic summary when AI is not configured.
    total = len(rows)
    training_count = sum(1 for row in rows if row["status"] == "training")
    leave_count = sum(1 for row in rows if row["status"] == "leave")
    return (
        f"- Total attendance records analyzed: {total}\n"
        f"- Training participation ratio: {round((training_count / total) * 100, 1)}%\n"
        f"- Leave cases observed: {leave_count}. Review recurring absences for intervention."
    )


def chat_with_attendance_assistant(db: Session, user: User, message: str) -> str:
    """Generate a conversational response from the attendance assistant."""
    # Fetch recent conversation history.
    # Newest-first from DB, then reverse to chronological order for stable multi-turn context.
    raw_turns = db.execute(
        select(Conversation.message, Conversation.response)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .limit(PLANNER_HISTORY_TURNS)
    ).all()

    conversation_history = [
        {"message": row[0], "response": row[1]} for row in reversed(raw_turns)
    ]
    first_interaction = len(conversation_history) == 0

    try:
        response = _run_sql_agent(db, user, message, conversation_history)
        if first_interaction:
            lowered = response.lower()
            has_greeting = lowered.startswith("hello") or lowered.startswith("hi") or lowered.startswith("hey")
            if not has_greeting:
                return f"Hello! {response}"
        return response
    except Exception as exc:
        # Ensure the SQLAlchemy session is usable for subsequent operations
        # (e.g., saving conversation) after any failed SQL execution.
        db.rollback()
        error_text = str(exc).lower()
        if "manager account is missing a team assignment" in error_text:
            return (
                "I can help with that, but your manager account is not linked to a team yet.\n"
                "Please ask an admin to assign your team, then try again."
            )
        if "access policy violation" in error_text:
            return (
                "I can only share data that matches your access level.\n"
                "Please try a request within your allowed scope."
            )
        return (
            "I'm sorry, I couldn't complete your request right now.\n"
            "Please rephrase your request, and I'll try again."
        )


def save_conversation(db: Session, user_id: int, message: str, response: str) -> Conversation:
    """Save a conversation exchange to the database."""
    conversation = Conversation(
        user_id=user_id,
        message=message,
        response=response,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


