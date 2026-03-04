"""
app.py — ADHD Productivity Hub
Run with: streamlit run app.py
"""
import datetime
import json
import random
import streamlit as st
import streamlit.components.v1 as components

import db
import ai_utils
import google_cal

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="ADHD Productivity Hub",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
/* ── Tab bar ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    height: 46px;
    padding: 0 18px;
    border-radius: 10px !important;
    font-weight: 600;
    font-size: 0.95em;
}
/* ── Metric cards ── */
div[data-testid="metric-container"] {
    background: #1e1e2e;
    border-radius: 12px;
    padding: 16px !important;
    border: 1px solid #2e2e4e;
}
/* ── Task row divider ── */
.task-divider { border: none; border-top: 1px solid #2e2e4e; margin: 4px 0; }
/* ── Priority badges ── */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.75em;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.badge-urgent { background: #450a0a; color: #fca5a5; }
.badge-high   { background: #431407; color: #fdba74; }
.badge-medium { background: #1c1917; color: #fde68a; }
.badge-low    { background: #052e16; color: #86efac; }
/* ── Habit streak ── */
.streak { color: #f97316; font-weight: 700; }
/* ── Quick capture ── */
div[data-testid="stTextInput"] > div > div > input[placeholder*="fast"],
div[data-testid="stTextInput"] > div > div > input[placeholder*="quickly"],
div[data-testid="stTextInput"] > div > div > input[placeholder*="anything"] {
    border-radius: 25px !important;
    padding-left: 20px !important;
}
/* ── Partner card ── */
.partner-card {
    background: #1e1e2e;
    border-radius: 14px;
    padding: 18px;
    text-align: center;
    border: 2px solid #3e3e6e;
    transition: border-color 0.2s;
}
.partner-card:hover { border-color: #7c3aed; }
</style>
""",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════

def _ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

db.init_db()
_ss("energy_level", db.get_setting("energy_level", "medium"))
_ss("bad_brain_day", db.get_setting("bad_brain_day", "false") == "true")
_ss("pomo_task_id", None)
_ss("pomo_task_title", "")
_ss("pomo_duration", 25)
_ss("pomo_phase", "focus")
_ss("pomo_session_count", 0)
_ss("expand_subtasks", {})
_ss("selected_priorities", [])
_ss("acct_active", False)
_ss("acct_start", None)
_ss("acct_goal", "")
_ss("acct_partner", None)
_ss("acct_duration", 60)
_ss("show_settings", False)


# ══════════════════════════════════════════════════════════════════════════════
# POMODORO TIMER HTML COMPONENT
# ══════════════════════════════════════════════════════════════════════════════

def _pomo_html(duration_seconds: int, phase: str, task_title: str) -> str:
    color = "#FF6B6B" if phase == "focus" else "#4ECDC4"
    bg = "#1a1a2e"
    label = "🍅 Focus Time" if phase == "focus" else "☕ Break Time"
    safe_title = task_title[:45] + ("…" if len(task_title) > 45 else "")

    return f"""
<div id="wrap" style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;
  text-align:center;padding:28px 24px;background:{bg};border-radius:20px;
  color:#fff;max-width:380px;margin:0 auto;
  box-shadow:0 12px 40px rgba(0,0,0,.45);">

  <div style="font-size:1.15em;color:{color};font-weight:700;margin-bottom:6px">{label}</div>
  <div style="font-size:.85em;color:#9ca3af;margin-bottom:18px;white-space:nowrap;
    overflow:hidden;text-overflow:ellipsis" title="{task_title}">{safe_title or "No task selected"}</div>

  <!-- Ring -->
  <div style="position:relative;display:inline-block;margin-bottom:18px">
    <svg width="160" height="160" viewBox="0 0 160 160">
      <circle cx="80" cy="80" r="72" fill="none" stroke="#2e2e4e" stroke-width="10"/>
      <circle id="ring" cx="80" cy="80" r="72" fill="none"
        stroke="{color}" stroke-width="10" stroke-linecap="round"
        stroke-dasharray="452.4" stroke-dashoffset="0"
        transform="rotate(-90 80 80)" style="transition:stroke-dashoffset 1s linear"/>
    </svg>
    <div id="disp" style="position:absolute;top:50%;left:50%;
      transform:translate(-50%,-50%);font-size:2.6em;font-weight:800;
      letter-spacing:2px;font-variant-numeric:tabular-nums">--:--</div>
  </div>

  <!-- Progress bar -->
  <div style="width:100%;height:6px;background:#2e2e4e;border-radius:3px;
    overflow:hidden;margin-bottom:16px">
    <div id="bar" style="height:100%;width:100%;background:{color};
      border-radius:3px;transition:width 1s linear"></div>
  </div>

  <div id="msg" style="min-height:24px;font-size:.9em;color:#9ca3af;
    margin-bottom:18px"></div>

  <div style="display:flex;gap:10px;justify-content:center">
    <button id="btn-toggle" onclick="toggle()" style="padding:11px 26px;
      background:{color};color:#fff;border:none;border-radius:25px;
      font-size:.95em;font-weight:700;cursor:pointer">▶ Start</button>
    <button onclick="reset()" style="padding:11px 26px;background:#374151;
      color:#fff;border:none;border-radius:25px;font-size:.95em;
      font-weight:700;cursor:pointer">↺ Reset</button>
  </div>

  <div id="done-msg" style="display:none;margin-top:18px;padding:14px;
    background:#064e3b;border-radius:10px;color:#6ee7b7;font-weight:700;
    font-size:1.05em">
    🎉 Session complete! Click <b>Log Session</b> in the sidebar to save it.
  </div>
</div>

<script>
const TOTAL = {duration_seconds};
let remaining = TOTAL, running = false, iv = null, done = false;
const CIRC = 2 * Math.PI * 72;  // ≈ 452.4

function fmt(s) {{
  const m = String(Math.floor(s/60)).padStart(2,'0');
  const sc = String(s%60).padStart(2,'0');
  return m+':'+sc;
}}

function draw() {{
  document.getElementById('disp').textContent = fmt(remaining);
  const pct = (TOTAL - remaining) / TOTAL;
  document.getElementById('ring').style.strokeDashoffset = pct * CIRC;
  document.getElementById('bar').style.width = ((1-pct)*100)+'%';
}}

function beep() {{
  try {{
    const ctx = new AudioContext();
    [880,660,880].forEach((f,i) => {{
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.type = 'sine'; o.frequency.value = f;
      g.gain.setValueAtTime(.4, ctx.currentTime + i*.35);
      g.gain.exponentialRampToValueAtTime(.001, ctx.currentTime + i*.35 + .5);
      o.start(ctx.currentTime + i*.35);
      o.stop(ctx.currentTime + i*.35 + .5);
    }});
  }} catch(e) {{}}
}}

function toggle() {{
  if (done) return;
  if (running) {{
    clearInterval(iv); running = false;
    document.getElementById('btn-toggle').textContent = '▶ Resume';
  }} else {{
    running = true;
    document.getElementById('btn-toggle').textContent = '⏸ Pause';
    iv = setInterval(() => {{
      remaining = Math.max(0, remaining-1);
      draw();
      const half = Math.floor(TOTAL/2);
      if (remaining === half)
        document.getElementById('msg').textContent = '💪 Halfway — keep going!';
      if (remaining <= 60 && remaining > 0)
        document.getElementById('msg').textContent = '⚡ Almost done!';
      if (remaining === 0) {{
        clearInterval(iv); running = false; done = true;
        beep();
        document.getElementById('btn-toggle').style.display = 'none';
        document.getElementById('done-msg').style.display = 'block';
        document.getElementById('msg').textContent = '';
      }}
    }}, 1000);
  }}
}}

function reset() {{
  clearInterval(iv); running = false; done = false; remaining = TOTAL;
  document.getElementById('btn-toggle').textContent = '▶ Start';
  document.getElementById('btn-toggle').style.display = '';
  document.getElementById('done-msg').style.display = 'none';
  document.getElementById('msg').textContent = '';
  draw();
}}

draw();
</script>
"""


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

PRIORITY_BADGE = {
    "urgent": '<span class="badge badge-urgent">🔴 urgent</span>',
    "high":   '<span class="badge badge-high">🟠 high</span>',
    "medium": '<span class="badge badge-medium">🟡 medium</span>',
    "low":    '<span class="badge badge-low">🟢 low</span>',
}
STATUS_ICON = {"pending": "⏳", "in_progress": "🔄", "done": "✅"}

BLOCK_TYPES = {
    "Deep Work":  ("🧠", "7", "#7c3aed"),
    "Admin":      ("📋", "1", "#2563eb"),
    "Meeting":    ("👥", "2", "#16a34a"),
    "Break":      ("☕", "5", "#d97706"),
    "Urgent":     ("🚨", "11", "#dc2626"),
}


# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# TAB RENDERERS
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

def render_dashboard():
    now = datetime.datetime.now()
    hour = now.hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
    st.markdown(f"## {greeting}! Let's set up your day 🌅")

    # ── Row 1: Energy + Bad Brain Day ──
    col_e, col_b = st.columns(2)

    with col_e:
        st.markdown("### ⚡ Energy Level")
        energy_opts = ["low", "medium", "high"]
        energy_labels = {"low": "🔋 Low", "medium": "⚡ Medium", "high": "🚀 High"}
        cur_idx = energy_opts.index(st.session_state.energy_level)
        energy = st.radio(
            "Energy",
            energy_opts,
            index=cur_idx,
            format_func=lambda x: energy_labels[x],
            horizontal=True,
            label_visibility="collapsed",
        )
        if energy != st.session_state.energy_level:
            st.session_state.energy_level = energy
            db.set_setting("energy_level", energy)

        st.info(ai_utils.ENERGY_SUGGESTIONS[energy])

    with col_b:
        st.markdown("### 🧠 Bad Brain Day")
        bad_brain = st.toggle(
            "Activate Bad Brain Day Mode",
            value=st.session_state.bad_brain_day,
        )
        if bad_brain != st.session_state.bad_brain_day:
            st.session_state.bad_brain_day = bad_brain
            db.set_setting("bad_brain_day", str(bad_brain).lower())
        if bad_brain:
            st.warning(
                "🤗 Task list capped at **3 items**. "
                "Be gentle with yourself — done is done."
            )
        else:
            st.success("✨ Full mode — you've got this!")

    st.divider()

    # ── Quick Capture ──
    st.markdown("### ⚡ Quick Capture")
    qc1, qc2 = st.columns([5, 1])
    with qc1:
        quick = st.text_input(
            "Quick capture",
            placeholder="What's on your mind? Add anything fast…",
            label_visibility="collapsed",
            key="dash_qc",
        )
    with qc2:
        if st.button("➕ Add", use_container_width=True, key="dash_qc_btn"):
            if quick.strip():
                db.add_task(quick.strip())
                st.toast(f"✅ Added: {quick.strip()}")
                st.rerun()

    st.divider()

    # ── Top Priorities ──
    st.markdown("### 🎯 Pick Your Top Priorities")
    pending_tasks = db.get_tasks(status="pending")
    task_cap = 3 if st.session_state.bad_brain_day else 5

    if pending_tasks:
        options = [t["title"] for t in pending_tasks]
        safe_defaults = [p for p in st.session_state.selected_priorities if p in options]

        selected = st.multiselect(
            f"Select up to {task_cap} priorities",
            options=options,
            default=safe_defaults[:task_cap],
            max_selections=task_cap,
            label_visibility="collapsed",
        )
        st.session_state.selected_priorities = selected

        if selected:
            for i, t in enumerate(selected, 1):
                st.markdown(f"**{i}.** {t}")

        # AI suggestions
        if st.button("🤖 AI Suggest Tasks"):
            with st.spinner("Claude is thinking…"):
                suggestions = ai_utils.ai_suggest_tasks(
                    st.session_state.energy_level,
                    [dict(t) for t in pending_tasks],
                    st.session_state.bad_brain_day,
                )
            if suggestions:
                st.info("💡 **AI Suggestions:** " + "  ·  ".join(suggestions))
            else:
                st.warning("Add your Anthropic API key in ⚙️ Settings to enable AI suggestions.")
    else:
        st.info("🎉 No pending tasks! Add some in the ✅ Tasks tab.")

    st.divider()

    # ── Stats ──
    all_tasks = db.get_tasks()
    today_iso = datetime.date.today().isoformat()
    done_today = [t for t in all_tasks if t["status"] == "done" and (t["completed_at"] or "")[:10] == today_iso]
    in_progress = [t for t in all_tasks if t["status"] == "in_progress"]
    pending_count = [t for t in all_tasks if t["status"] == "pending"]
    focus_today = db.get_focus_minutes_by_day(1).get(today_iso, 0)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("✅ Done Today", len(done_today))
    m2.metric("🔄 In Progress", len(in_progress))
    m3.metric("📋 Pending", len(pending_count))
    m4.metric("🍅 Focus Min", f"{focus_today}m")

    st.divider()

    # ── Calendar preview ──
    st.markdown("### 📅 Today's Calendar")
    cal_service = google_cal.get_service()
    if cal_service:
        events = google_cal.get_upcoming_events(cal_service, max_results=8)
        today_events = [
            e for e in events
            if (e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", ""))[:10] == today_iso
        ]
        if today_events:
            for ev in today_events:
                time_str = google_cal.format_event_time(ev)
                st.markdown(f"🗓 **{time_str}** — {ev.get('summary', 'No title')}")
        else:
            st.info("No events scheduled for today.")
    else:
        st.info("📅 Connect Google Calendar in the **📅 Calendar** tab to see today's events here.")

    # ── EOD Review (after 4 pm) ──
    if hour >= 16:
        st.divider()
        st.markdown("### 🌙 End of Day Review")
        existing = db.get_today_eod()
        if existing:
            stars_str = "⭐" * existing["stars"]
            st.success(f"Already reviewed today! {stars_str}")
            st.write(f"*{existing['reflection']}*")
        else:
            stars = st.select_slider(
                "How was your day?",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: "⭐" * x,
            )
            reflection = st.text_area(
                "Quick reflection…",
                placeholder="What went well? What's one thing you'd change?",
                height=100,
            )
            if st.button("💾 Save Review", type="primary"):
                if reflection.strip():
                    db.save_eod_review(stars, reflection.strip())
                    st.success("🌅 Great work today! Rest well — see you tomorrow.")
                    st.rerun()
                else:
                    st.error("Add a short reflection first.")


# ─── TASKS ────────────────────────────────────────────────────────────────────

def render_tasks():
    st.markdown("## ✅ Tasks")

    # ── Quick capture ──
    qc1, qc2 = st.columns([5, 1])
    with qc1:
        quick = st.text_input(
            "Quick add",
            placeholder="Type a task and press ➕ Add…",
            label_visibility="collapsed",
            key="tasks_qc",
        )
    with qc2:
        if st.button("➕ Add", use_container_width=True, key="tasks_qc_btn"):
            if quick.strip():
                db.add_task(quick.strip())
                st.toast("✅ Task added!")
                st.rerun()

    # ── Detailed add ──
    with st.expander("📋 Add with Details"):
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            d_title = st.text_input("Task title *", key="d_title")
            d_priority = st.selectbox("Priority", ["medium", "high", "urgent", "low"], key="d_prio")
        with dc2:
            d_cat = st.selectbox(
                "Category",
                ["general", "work", "personal", "health", "creative", "learning", "errands"],
                key="d_cat",
            )
            d_energy = st.selectbox("Energy Required", ["medium", "low", "high"], key="d_energy")
        with dc3:
            d_due = st.date_input("Due Date (optional)", value=None, key="d_due")
            d_pomos = st.number_input("Est. Pomodoros 🍅", min_value=1, max_value=20, value=1, key="d_pomos")

        if st.button("➕ Add Task", type="primary", key="d_add_btn"):
            if d_title.strip():
                due_str = str(d_due) if d_due else None
                db.add_task(d_title.strip(), d_priority, d_cat, due_str, d_energy, d_pomos)
                st.toast("✅ Task added!")
                st.rerun()
            else:
                st.error("Please enter a task title.")

    st.divider()

    # ── Filters ──
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_status = st.selectbox("Status", ["all", "pending", "in_progress", "done"], key="f_status")
    with fc2:
        f_cat = st.selectbox(
            "Category",
            ["all", "general", "work", "personal", "health", "creative", "learning", "errands", "from_note"],
            key="f_cat",
        )
    with fc3:
        f_prio = st.selectbox("Priority", ["all", "urgent", "high", "medium", "low"], key="f_prio")

    tasks = db.get_tasks(
        status=None if f_status == "all" else f_status,
        category=None if f_cat == "all" else f_cat,
        priority=None if f_prio == "all" else f_prio,
    )

    if not tasks:
        st.info("No tasks found. Add one above!")
        st.divider()
    else:
        for task in tasks:
            tid = task["id"]
            badge = PRIORITY_BADGE.get(task["priority"], "")
            si = STATUS_ICON.get(task["status"], "⏳")

            # ── Task row ──
            row = st.container()
            with row:
                c_title, c_done, c_start, c_pomo, c_sub, c_del = st.columns(
                    [4, 0.6, 0.6, 0.6, 0.6, 0.6]
                )
                with c_title:
                    title_md = f"{si} **{task['title']}**"
                    st.markdown(title_md)
                    meta = []
                    if task["category"] != "general":
                        meta.append(f"📁 {task['category']}")
                    if task["due_date"]:
                        meta.append(f"📅 {task['due_date']}")
                    pomo_str = f"🍅 {task['pomodoros_done']}/{task['pomodoros_estimated']}"
                    meta.append(pomo_str)
                    st.markdown(
                        badge + ("  " if meta else "") + "  ·  ".join(meta),
                        unsafe_allow_html=True,
                    )

                with c_done:
                    if task["status"] != "done":
                        if st.button("✓", key=f"done_{tid}", help="Mark done"):
                            db.update_task_status(tid, "done")
                            st.rerun()

                with c_start:
                    if task["status"] == "pending":
                        if st.button("▶", key=f"start_{tid}", help="Start task"):
                            db.update_task_status(tid, "in_progress")
                            st.rerun()

                with c_pomo:
                    if st.button("🍅", key=f"pomo_{tid}", help="Focus on this task"):
                        st.session_state.pomo_task_id = tid
                        st.session_state.pomo_task_title = task["title"]
                        st.toast("Switch to the 🍅 Pomodoro tab — task pre-selected!")

                with c_sub:
                    expand_key = f"exp_{tid}"
                    cur = st.session_state.expand_subtasks.get(tid, False)
                    icon = "📂" if cur else "📋"
                    if st.button(icon, key=f"sub_{tid}", help="Toggle subtasks"):
                        st.session_state.expand_subtasks[tid] = not cur
                        st.rerun()

                with c_del:
                    if st.button("🗑", key=f"del_{tid}", help="Delete task"):
                        db.delete_task(tid)
                        st.rerun()

            # ── Subtasks (expanded) ──
            if st.session_state.expand_subtasks.get(tid, False):
                with st.container():
                    st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;**Subtasks:**")
                    subtasks = db.get_subtasks(tid)
                    for sub in subtasks:
                        sc1, sc2 = st.columns([5, 1])
                        with sc1:
                            done_val = st.checkbox(
                                sub["title"],
                                value=bool(sub["done"]),
                                key=f"subck_{sub['id']}",
                            )
                            if done_val != bool(sub["done"]):
                                db.toggle_subtask(sub["id"], done_val)
                                st.rerun()
                        with sc2:
                            if st.button("🗑", key=f"delsub_{sub['id']}"):
                                db.delete_subtask(sub["id"])
                                st.rerun()

                    ns1, ns2 = st.columns([5, 1])
                    with ns1:
                        new_sub = st.text_input(
                            "New subtask",
                            placeholder="Add subtask…",
                            label_visibility="collapsed",
                            key=f"newsub_{tid}",
                        )
                    with ns2:
                        if st.button("Add", key=f"addsub_{tid}"):
                            if new_sub.strip():
                                db.add_subtask(tid, new_sub.strip())
                                st.rerun()

            st.markdown('<hr class="task-divider">', unsafe_allow_html=True)

    # ── Habits ──
    st.markdown("## 🔁 Daily Habits")
    habits = db.get_habits()

    if habits:
        for h in habits:
            hc1, hc2, hc3 = st.columns([3, 1.5, 0.6])
            done_today = db.get_habit_done_today(h["id"])
            streak = db.get_habit_streak(h["id"])
            with hc1:
                checked = st.checkbox(
                    f"{h['icon']} {h['name']}",
                    value=done_today,
                    key=f"hab_{h['id']}",
                )
                if checked != done_today:
                    db.toggle_habit_today(h["id"], checked)
                    st.rerun()
            with hc2:
                if streak > 0:
                    st.markdown(f'<span class="streak">🔥 {streak}-day streak</span>', unsafe_allow_html=True)
            with hc3:
                if st.button("🗑", key=f"delhab_{h['id']}"):
                    db.delete_habit(h["id"])
                    st.rerun()

    with st.expander("➕ Add New Habit"):
        nh1, nh2, nh3 = st.columns([3, 1, 1])
        with nh1:
            new_hname = st.text_input("Habit name", key="new_hname")
        with nh2:
            new_hicon = st.selectbox(
                "Icon",
                ["✅", "💪", "🏃", "🧘", "📚", "💧", "🥗", "😴", "🎯", "🌟", "🧹", "☀️"],
                key="new_hicon",
            )
        with nh3:
            st.write("")
            if st.button("Add Habit", key="add_habit_btn"):
                if new_hname.strip():
                    db.add_habit(new_hname.strip(), new_hicon)
                    st.toast(f"Habit '{new_hname}' added!")
                    st.rerun()


# ─── NOTES ────────────────────────────────────────────────────────────────────

def render_notes():
    st.markdown("## 📝 Notes & Brain Dump")

    # ── Brain Dump ──
    st.markdown("### 🧠 Brain Dump")
    auto_analyze = st.checkbox(
        "🤖 Auto-analyze with AI — extract tags, summary & action items (added as tasks)",
        value=False,
        key="auto_analyze",
    )
    brain_dump = st.text_area(
        "Brain dump",
        height=200,
        placeholder="Paste anything — voice transcript, meeting notes, random ideas, worries…",
        label_visibility="collapsed",
        key="brain_dump_input",
    )

    bc1, bc2 = st.columns([1, 4])
    with bc1:
        save_clicked = st.button("💾 Save Note", type="primary", use_container_width=True)

    if save_clicked:
        if not brain_dump.strip():
            st.error("Nothing to save!")
        elif auto_analyze:
            with st.spinner("🤖 Claude is analyzing your note…"):
                tags, summary, action_items = ai_utils.ai_analyze_note(brain_dump.strip())

            if tags is not None:
                note_id = db.save_note(brain_dump.strip(), tags, summary)
                if action_items:
                    db.save_note_actions(note_id, action_items)

                st.success("✅ Note saved and analyzed!")
                if summary:
                    st.info(f"**Summary:** {summary}")
                if tags:
                    tag_html = " ".join([f'`{t}`' for t in tags])
                    st.write("**Tags:** " + "  ".join(tags))
                if action_items:
                    st.markdown("**Action Items Extracted → added as tasks:**")
                    for item in action_items:
                        st.markdown(f"  - ✅ {item}")
                st.rerun()
            else:
                st.error(f"AI analysis failed: {summary}")
                note_id = db.save_note(brain_dump.strip())
                st.warning("Note saved without analysis.")
                st.rerun()
        else:
            db.save_note(brain_dump.strip())
            st.toast("✅ Note saved!")
            st.rerun()

    st.divider()

    # ── Note Library ──
    st.markdown("### 📚 Note Library")
    search = st.text_input(
        "Search",
        placeholder="🔍 Search notes by content or tag…",
        label_visibility="collapsed",
        key="note_search",
    )

    notes = db.get_notes()
    if search.strip():
        q = search.strip().lower()
        notes = [
            n for n in notes
            if q in (n["content"] or "").lower() or q in (n["tags"] or "").lower()
        ]

    if not notes:
        st.info("No notes yet. Start with the Brain Dump above!")
    else:
        for note in notes:
            preview = (note["content"] or "")[:70].replace("\n", " ")
            label = f"📝 {note['created_at'][:16]}  —  {preview}…"
            with st.expander(label):
                st.text_area(
                    "Content",
                    value=note["content"] or "",
                    height=120,
                    disabled=True,
                    key=f"nc_{note['id']}",
                )
                if note["summary"]:
                    st.info(f"**Summary:** {note['summary']}")

                tags_raw = note["tags"] or "[]"
                try:
                    tags_list = json.loads(tags_raw)
                except Exception:
                    tags_list = []
                if tags_list:
                    st.write("**Tags:** " + "  ·  ".join(tags_list))

                # Per-note actions
                na1, na2 = st.columns([1, 1])
                with na1:
                    if st.button("🤖 Analyze", key=f"an_{note['id']}"):
                        with st.spinner("Analyzing…"):
                            tags, summary, actions = ai_utils.ai_analyze_note(note["content"] or "")
                        if tags is not None:
                            db.update_note_analysis(note["id"], tags, summary)
                            if actions:
                                db.save_note_actions(note["id"], actions)
                            st.success("✅ Analysis complete!")
                            st.rerun()
                        else:
                            st.error(f"Failed: {summary}")
                with na2:
                    if st.button("🗑 Delete", key=f"dn_{note['id']}"):
                        db.delete_note(note["id"])
                        st.rerun()


# ─── CALENDAR ─────────────────────────────────────────────────────────────────

def render_calendar():
    st.markdown("## 📅 Calendar")

    if not google_cal.is_available():
               st.error(
            "Google Calendar libraries not installed.\n\n"
            "Run: `pip install google-auth-oauthlib google-api-python-client`"
        )
                return
    # Auto-detect OAuth code from URL redirect
                # Auto-detect OAuth code from URL redirect
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params["code"]
        try:
            google_cal.exchange_code_for_token(auth_code)
            # Clear query params after successful exchange
            st.query_params.clear()
            st.success("✅ Connected to Google Calendar!")
            st.rerun()
        except Exception as e:
            st.error(f"Authorization failed: {e}")
            "Run: `pip install google-auth-oauthlib google-api-python-client`"
        )
        return

    cal_service = google_cal.get_service()

    # ── Connection status ──
    if cal_service:
        st.success("✅ Connected to Google Calendar")
        if st.button("🔌 Disconnect"):
            google_cal.disconnect()
            st.rerun()
    else:
        st.warning("📅 Google Calendar not connected.")

        with st.expander("📋 Setup Instructions", expanded=not google_cal.has_credentials_file()):
            st.markdown(
                """
**Steps to connect Google Calendar:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the **Google Calendar API** (APIs & Services → Library)
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client IDs**
5. Set application type to **Desktop app**, name it anything
6. Click **Download JSON** and rename the file to `credentials.json`
7. Place `credentials.json` in the same folder as `app.py`
8. Click **Connect Google Calendar** below — a browser window will open for authorization

**Your app folder:** the folder you selected when opening this app.
"""
            )

        if google_cal.has_credentials_file():
                if "oauth_url" not in st.session_state:
                    if st.button("🖗 Connect Google Calendar", type="primary"):
                        try:
                            _, auth_url = google_cal.get_auth_url()
                            st.session_state["oauth_url"] = auth_url
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to start authorization: {e}")
                else:
                    st.info("🔗 **Step 1:** Click the link below to authorize Google Calendar:")
                    st.markdown(f"[Click here to authorize]({st.session_state['oauth_url']})")
                st.info("🔗 After authorizing, you'll be redirected back to this app automatically.")
                if st.button("❌ Cancel"):
                    del st.session_state["oauth_url"]
                    st.rerun()                            del st.session_state["oauth_url"]
                            st.rerun()
        else:
            st.info("📁 Place `credentials.json` in your app folder, then return here.")
    st.divider()
    st.markdown("### ➕ Add Time Block")
    with st.expander("Add a new time block"):
        tb1, tb2, tb3 = st.columns(3)
        with tb1:
            tb_title = st.text_input("Title", placeholder="e.g. Deep Work — Report", key="tb_title")
            tb_type = st.selectbox("Type", list(BLOCK_TYPES.keys()), key="tb_type")
    with tb2:
            tb_date = st.date_input("Date", value=datetime.date.today(), key="tb_date")
            tb_start = st.time_input("Start time", value=datetime.time(9, 0), key="tb_start")
    with tb3:
            tb_end = st.time_input("End time", value=datetime.time(10, 0), key="tb_end")
            tb_gcal = st.checkbox("Sync to Google Calendar", value=bool(cal_service), key="tb_gcal")

    if st.button("➕ Add Time Block", type="primary", key="add_tb_btn"):
        if not tb_title.strip():
            st.error("Enter a block title.")
        elif tb_start >= tb_end:
            st.error("End time must be after start time.")
        else:
            gcal_id = None
            emoji, color_id, _ = BLOCK_TYPES[tb_type]
            if tb_gcal and cal_service:
                start_dt = datetime.datetime.combine(tb_date, tb_start)
                end_dt = datetime.datetime.combine(tb_date, tb_end)
                try:
                    gcal_id = google_cal.create_event(
                        cal_service,
                        f"{emoji} {tb_title}",
                        start_dt,
                        end_dt,
                        description=f"Time block: {tb_type}",
                        color_id=color_id,
                    )
                except Exception as e:
                    st.warning(f"Couldn't add to Google Calendar: {e}")

            db.add_time_block(
                tb_title.strip(), tb_type,
                str(tb_start), str(tb_end),
                str(tb_date), gcal_id,
            )
            msg = "✅ Block added and synced to Google Calendar!" if gcal_id else "✅ Block added locally."
            st.toast(msg)
            st.rerun()

    st.divider()

    # ── Upcoming Events ──
    if cal_service:
        st.markdown("### 📆 Upcoming Events")
        events = google_cal.get_upcoming_events(cal_service, max_results=25)

        if events:
            from collections import defaultdict
            by_day = defaultdict(list)
            for ev in events:
                start_str = (ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date", ""))
                by_day[start_str[:10]].append(ev)

            for day in sorted(by_day.keys()):
                try:
                    d = datetime.date.fromisoformat(day)
                    today = datetime.date.today()
                    if d == today:
                        day_label = f"🟢 Today — {d.strftime('%A, %B %d')}"
                    elif d == today + datetime.timedelta(days=1):
                        day_label = f"🔵 Tomorrow — {d.strftime('%A, %B %d')}"
                    else:
                        day_label = f"📅 {d.strftime('%A, %B %d')}"
                except Exception:
                    day_label = day

                st.markdown(f"**{day_label}**")
                for ev in by_day[day]:
                    time_str = google_cal.format_event_time(ev)
                    ev_col1, ev_col2 = st.columns([6, 1])
                    with ev_col1:
                        st.markdown(f"&nbsp;&nbsp;🗓 **{time_str}** — {ev.get('summary', 'No title')}")
                    with ev_col2:
                        if st.button("🗑", key=f"gcal_del_{ev['id']}"):
                            google_cal.delete_event(cal_service, ev["id"])
                            st.toast("Event deleted.")
                            st.rerun()
                st.write("")
        else:
            st.info("No upcoming events.")

    # ── Local Time Blocks ──
    st.markdown("### 📋 Local Time Blocks")
    blocks = db.get_time_blocks()
    if blocks:
        for blk in blocks:
            emoji, _, color = BLOCK_TYPES.get(blk["block_type"], ("📋", "1", "#666"))
            bc1, bc2 = st.columns([6, 1])
            with bc1:
                gcal_dot = "🔗" if blk["google_event_id"] else "💾"
                st.markdown(
                    f"{emoji} **{blk['date']}** · {blk['start_time'][:5]}–{blk['end_time'][:5]} "
                    f"· {blk['title']} `{blk['block_type']}` {gcal_dot}"
                )
            with bc2:
                if st.button("🗑", key=f"del_blk_{blk['id']}"):
                    gcal_event_id = db.delete_time_block(blk["id"])
                    if gcal_event_id and cal_service:
                        google_cal.delete_event(cal_service, gcal_event_id)
                    st.rerun()
    else:
        st.info("No local time blocks yet.")


# ─── POMODORO ─────────────────────────────────────────────────────────────────

def render_pomodoro():
    st.markdown("## 🍅 Pomodoro Timer")

    ctrl_col, timer_col = st.columns([1, 1.6])

    with ctrl_col:
        st.markdown("### 🎯 Task")
        active_tasks = [t for t in db.get_tasks() if t["status"] in ("pending", "in_progress")]
        task_map = {"(No task selected)": None}
        for t in active_tasks:
            label = t["title"][:55] + ("…" if len(t["title"]) > 55 else "")
            task_map[label] = t["id"]

        # Try to pre-select the task set from Tasks tab
        default_idx = 0
        if st.session_state.pomo_task_title:
            for i, name in enumerate(task_map.keys()):
                if st.session_state.pomo_task_title in name:
                    default_idx = i
                    break

        sel_name = st.selectbox(
            "Select task",
            list(task_map.keys()),
            index=default_idx,
            label_visibility="collapsed",
            key="pomo_task_select",
        )
        st.session_state.pomo_task_id = task_map.get(sel_name)
        st.session_state.pomo_task_title = sel_name if sel_name != "(No task selected)" else ""

        st.markdown("### ⏱ Duration")
        phase = st.radio(
            "Phase",
            ["focus", "break"],
            index=0 if st.session_state.pomo_phase == "focus" else 1,
            format_func=lambda x: "🍅 Focus" if x == "focus" else "☕ Break",
            horizontal=True,
            key="pomo_phase_radio",
        )
        st.session_state.pomo_phase = phase

        if phase == "focus":
            dur = st.slider("Focus minutes", 15, 50, st.session_state.pomo_duration, 5, key="pomo_dur_slider")
            st.session_state.pomo_duration = dur
            timer_secs = dur * 60
        else:
            long_break = st.session_state.pomo_session_count > 0 and st.session_state.pomo_session_count % 4 == 0
            break_dur = 15 if long_break else 5
            timer_secs = break_dur * 60
            if long_break:
                st.info(f"🎉 Long break ({break_dur} min) — you've earned it!")
            else:
                st.info(f"☕ Short break ({break_dur} min)")

        st.divider()
        st.markdown("### 📋 Session Log")
        sessions_done = st.session_state.pomo_session_count
        st.metric("Sessions this run", f"{sessions_done} 🍅")

        if st.button("✅ Log Completed Session", use_container_width=True, type="primary"):
            log_dur = st.session_state.pomo_duration if phase == "focus" else break_dur
            db.log_pomodoro(
                st.session_state.pomo_task_id,
                st.session_state.pomo_task_title,
                log_dur,
                phase,
            )
            if phase == "focus":
                st.session_state.pomo_session_count += 1
                st.session_state.pomo_phase = "break"
                st.toast(f"🍅 Focus session logged! Take a break.")
            else:
                st.session_state.pomo_phase = "focus"
                st.toast("☕ Break logged! Ready for the next focus session.")
            st.rerun()

        if st.button("↺ Refresh State", use_container_width=True):
            st.rerun()

    with timer_col:
        st.markdown("### ⏰ Timer")
        components.html(
            _pomo_html(timer_secs, phase, st.session_state.pomo_task_title),
            height=440,
        )
        st.caption(
            "⚡ Timer runs entirely in your browser. "
            "After the session ends, click **Log Completed Session** on the left to save it."
        )

    st.divider()

    # ── Session history ──
    st.markdown("### 📊 Session History")
    sessions = db.get_pomodoro_sessions(15)
    if sessions:
        for s in sessions:
            icon = "🍅" if s["phase"] == "focus" else "☕"
            when = (s["completed_at"] or "")[:16]
            title = s["task_title"] or "—"
            st.markdown(f"{icon} **{title}** · {s['duration_minutes']} min · {when}")
    else:
        st.info("No sessions logged yet. Complete your first Pomodoro!")

    st.divider()

    # ── 7-day bar chart ──
    st.markdown("### 📈 Focus Minutes — Last 7 Days")
    focus_data = db.get_focus_minutes_by_day(7)
    if focus_data:
        import pandas as pd
        dates = [(datetime.date.today() - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        df = pd.DataFrame({
            "Date": [d[-5:] for d in dates],
            "Focus Minutes": [focus_data.get(d, 0) for d in dates],
        }).set_index("Date")
        st.bar_chart(df)
    else:
        st.info("Complete some sessions to see your focus chart!")


# ─── ACCOUNTABILITY ───────────────────────────────────────────────────────────

def render_accountability():
    st.markdown("## 👥 Accountability Partner")

    if not st.session_state.acct_active:
        # ── Setup ──
        st.markdown("### Start a Session")

        sc1, sc2 = st.columns(2)
        with sc1:
            goal = st.text_area(
                "What's your specific goal for this session?",
                placeholder="e.g., Finish the intro section of my report and outline the next three paragraphs",
                height=120,
                key="acct_goal_input",
            )
            dur_opts = {"30 min": 30, "45 min": 45, "60 min": 60, "90 min": 90, "2 hours": 120}
            dur_label = st.selectbox("Session length", list(dur_opts.keys()), index=2, key="acct_dur_sel")
            dur_val = dur_opts[dur_label]

        with sc2:
            st.markdown("**Choose your virtual partner:**")
            for i, partner in enumerate(ai_utils.VIRTUAL_PARTNERS):
                selected = st.session_state.acct_partner and st.session_state.acct_partner["name"] == partner["name"]
                border = f"border: 2px solid {partner['color']};" if selected else ""
                if st.button(
                    f"{partner['emoji']} {partner['name']} — {partner['tagline']}",
                    key=f"pick_partner_{i}",
                    use_container_width=True,
                ):
                    st.session_state.acct_partner = partner
                    st.rerun()

            if st.session_state.acct_partner:
                p = st.session_state.acct_partner
                st.success(f"Selected: {p['emoji']} **{p['name']}** ({p['style']})")

        st.divider()
        if st.button("🚀 Start Session", type="primary", use_container_width=True):
            errors = []
            if not (goal or "").strip():
                errors.append("Set a specific goal.")
            if not st.session_state.acct_partner:
                errors.append("Choose a virtual partner.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.session_state.acct_active = True
                st.session_state.acct_start = datetime.datetime.now()
                st.session_state.acct_goal = goal.strip()
                st.session_state.acct_duration = dur_val
                st.rerun()

    else:
        # ── Active session ──
        partner = st.session_state.acct_partner
        goal = st.session_state.acct_goal
        duration = st.session_state.acct_duration
        start = st.session_state.acct_start

        now = datetime.datetime.now()
        elapsed_s = (now - start).total_seconds()
        total_s = duration * 60
        remaining_s = max(0, total_s - elapsed_s)
        progress = min(1.0, elapsed_s / total_s)
        elapsed_min = int(elapsed_s / 60)
        rem_min = int(remaining_s / 60)
        rem_sec = int(remaining_s % 60)

        # Partner display
        pc1, pc2 = st.columns([1, 4])
        with pc1:
            st.markdown(
                f'<div style="font-size:4.5em;text-align:center;'
                f'background:#1e1e2e;border-radius:14px;padding:16px;'
                f'border:2px solid {partner["color"]}">{partner["emoji"]}</div>',
                unsafe_allow_html=True,
            )
        with pc2:
            st.markdown(f"### {partner['emoji']} {partner['name']} is with you 💪")
            st.markdown(f"*{partner['tagline']}*")
            st.info(f"🎯 **Your goal:** {goal}")

        st.divider()

        # Timer display
        if remaining_s > 0:
            st.markdown(f"## ⏱ {rem_min:02d}:{rem_sec:02d} remaining")
            st.progress(progress)
            st.caption(f"Elapsed: {elapsed_min} min of {duration} min")

            # Midpoint quote
            if 0.45 <= progress <= 0.58:
                st.success(f"💫 **Midpoint!** {partner['midpoint_quote']}")
        else:
            st.success("🎉 **Session Complete!** Fantastic work!")
            st.balloons()

        if st.button("↺ Refresh Timer"):
            st.rerun()

        st.divider()

        # End session
        refc1, refc2 = st.columns([2, 1])
        with refc1:
            reflection = st.text_area(
                "Session reflection:",
                placeholder="What did you accomplish? Any blockers or wins to note?",
                height=100,
                key="acct_reflection",
            )
        with refc2:
            st.write("")
            st.write("")
            if st.button("✅ Complete Session", type="primary", use_container_width=True):
                focus_min = min(elapsed_min, duration)
                db.save_accountability_session(
                    goal, partner["name"], duration, focus_min, reflection
                )
                st.session_state.acct_active = False
                st.session_state.acct_start = None
                st.session_state.acct_goal = ""
                st.session_state.acct_partner = None
                st.toast(f"🎉 Great work! {focus_min} minutes with {partner['name']}.")
                st.rerun()

            if st.button("⏹ End Early", use_container_width=True):
                st.session_state.acct_active = False
                st.session_state.acct_start = None
                st.rerun()

    st.divider()

    # ── 7-day chart ──
    st.markdown("### 📊 Focus Minutes — Last 7 Days")
    acct_data = db.get_accountability_focus_by_day(7)
    if acct_data:
        import pandas as pd
        dates = [(datetime.date.today() - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        df = pd.DataFrame({
            "Date": [d[-5:] for d in dates],
            "Focus Minutes": [acct_data.get(d, 0) for d in dates],
        }).set_index("Date")
        st.bar_chart(df)
    else:
        st.info("Complete sessions to see your focus chart here!")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    db.init_db()

    # ── Header ──
    h1, h2, h3 = st.columns([4, 1.2, 1])
    with h1:
        st.markdown("# 🧠 ADHD Productivity Hub")
    with h2:
        today_str = datetime.date.today().strftime("%a, %b %d")
        st.markdown(f"<div style='padding-top:18px;color:#9ca3af'>{today_str}</div>", unsafe_allow_html=True)
    with h3:
        if st.button("⚙️ Settings", use_container_width=True):
            st.session_state.show_settings = not st.session_state.get("show_settings", False)

    # ── Settings panel ──
    if st.session_state.get("show_settings", False):
        with st.expander("⚙️ Settings", expanded=True):
            saved_key = db.get_setting("anthropic_api_key", "")
            api_key = st.text_input(
                "Anthropic API Key",
                value=saved_key,
                type="password",
                help="Required for AI note analysis and task suggestions",
            )
            if st.button("💾 Save API Key"):
                db.set_setting("anthropic_api_key", api_key)
                st.success("✅ API key saved!")
                st.rerun()

            if saved_key:
                st.success("✅ API key configured.")
            else:
                st.warning("No API key set. AI features will be disabled.")

    # ── Tabs ──
    tabs = st.tabs([
        "🏠 Dashboard",
        "✅ Tasks",
        "📝 Notes",
        "📅 Calendar",
        "🍅 Pomodoro",
        "👥 Accountability",
    ])

    with tabs[0]:
        render_dashboard()
    with tabs[1]:
        render_tasks()
    with tabs[2]:
        render_notes()
    with tabs[3]:
        render_calendar()
    with tabs[4]:
        render_pomodoro()
    with tabs[5]:
        render_accountability()


if __name__ == "__main__":
    main()
