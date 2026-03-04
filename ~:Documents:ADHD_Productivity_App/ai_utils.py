"""
ai_utils.py — Anthropic Claude integration for ADHD Productivity App
"""
import json
import random
from db import get_setting

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


VIRTUAL_PARTNERS = [
    {
        "name": "Alex",
        "emoji": "🧑‍💼",
        "style": "Analytical",
        "tagline": "Data-driven and methodical",
        "midpoint_quote": "You're 50% there — statistically, momentum is on your side.",
        "color": "#4F46E5",
    },
    {
        "name": "Sam",
        "emoji": "🌟",
        "style": "Encouraging",
        "tagline": "Your biggest cheerleader",
        "midpoint_quote": "Halfway! You're doing AMAZING — keep that energy going!",
        "color": "#D97706",
    },
    {
        "name": "Jordan",
        "emoji": "🎯",
        "style": "Focused",
        "tagline": "Sharp, direct, no fluff",
        "midpoint_quote": "Halfway point. Lock in. No distractions — you know what to do.",
        "color": "#059669",
    },
    {
        "name": "River",
        "emoji": "🌊",
        "style": "Calm",
        "tagline": "Steady, grounding presence",
        "midpoint_quote": "Halfway through. Breathe. You're flowing right where you need to be.",
        "color": "#0284C7",
    },
]

MOTIVATIONAL_QUOTES = [
    "The secret of getting ahead is getting started.",
    "Focus on progress, not perfection.",
    "One task at a time. One moment at a time.",
    "You don't have to be great to start, but you have to start to be great.",
    "Done is better than perfect.",
    "Your brain is full of ideas — let's get one of them done.",
    "Small steps taken consistently create big results.",
    "Every expert was once a beginner. Keep going.",
]

ENERGY_SUGGESTIONS = {
    "low": "🔋 Low energy today — try admin tasks, emails, or anything that doesn't need deep focus.",
    "medium": "⚡ Medium energy — good for regular work tasks and steady progress.",
    "high": "🚀 High energy — perfect for deep work, creative projects, and challenging tasks!",
}


def get_client():
    if not ANTHROPIC_AVAILABLE:
        return None
    # Check Streamlit secrets first (for cloud deployment), then fall back to DB setting
    api_key = None
    try:
        import streamlit as st
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass
    if not api_key:
        api_key = get_setting("anthropic_api_key")
    if not api_key:
        return None
    try:
        return anthropic.Anthropic(api_key=api_key)
    except Exception:
        return None


def ai_analyze_note(content: str):
    """
    Returns (tags: list, summary: str, action_items: list).
    On failure returns (None, error_msg, []).
    """
    client = get_client()
    if not client:
        return None, "No API key configured — add it in ⚙️ Settings", []

    prompt = f"""Analyze this note and return a JSON object with exactly these three keys:
- "tags": array of 3-6 short relevant tags (strings)
- "summary": a 1-2 sentence summary of the main content
- "action_items": an array of clear, actionable tasks extracted from the note (0-8 items)

Note content:
{content}

Return ONLY valid JSON. No markdown, no explanation, just the JSON object."""

    try:
        message = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        return (
            result.get("tags", []),
            result.get("summary", ""),
            result.get("action_items", []),
        )
    except json.JSONDecodeError as e:
        return None, f"AI returned invalid JSON: {e}", []
    except Exception as e:
        return None, f"AI error: {e}", []


def ai_suggest_tasks(energy_level: str, pending_tasks: list, bad_brain_day: bool = False):
    """
    Returns a list of task titles (strings) suggested for today.
    Returns empty list on failure.
    """
    client = get_client()
    if not client or not pending_tasks:
        return []

    cap = 3 if bad_brain_day else 5
    task_list = "\n".join(
        [
            f"- {t['title']} (priority: {t['priority']}, energy: {t['energy_level']}, due: {t['due_date'] or 'none'})"
            for t in pending_tasks[:25]
        ]
    )

    bad_brain_note = "Note: This is a Bad Brain Day — prefer gentle, low-cognitive-load tasks." if bad_brain_day else ""

    prompt = f"""You are an ADHD productivity coach. The user has {energy_level} energy today.
{bad_brain_note}

Here are their pending tasks:
{task_list}

Suggest the {cap} most appropriate tasks to focus on today, matching energy level and priority.
Return ONLY a JSON array of task title strings, exactly as they appear in the list above.
Example: ["Task A", "Task B", "Task C"]"""

    try:
        message = client.messages.create(
            model="claude-opus-4-5-20251101",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception:
        return []


def get_random_quote():
    return random.choice(MOTIVATIONAL_QUOTES)
