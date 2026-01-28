import streamlit as st
from datetime import datetime, timedelta
import threading
import time
from queue import Queue, Empty

# --- Page Config ---
st.set_page_config(
    page_title="Agent Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
agents = ["Listener", "Planner", "Executor"]

if "agent_status" not in st.session_state:
    st.session_state.agent_status = {agent: "idle" for agent in agents}

if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = {agent: [] for agent in agents}

if "last_heartbeat" not in st.session_state:
    st.session_state.last_heartbeat = {agent: None for agent in agents}

if "agent_threads" not in st.session_state:
    st.session_state.agent_threads = {}

if "agent_queues" not in st.session_state:
    st.session_state.agent_queues = {agent: Queue() for agent in agents}

if "agent_progress" not in st.session_state:
    st.session_state.agent_progress = {agent: 0.0 for agent in agents}


# --- Helper Functions ---
def agent_worker(agent_name):
    """Background worker that processes tasks from the agent's queue with progress"""
    while st.session_state.agent_status[agent_name] == "running":
        try:
            task = st.session_state.agent_queues[agent_name].get(timeout=1)
        except Empty:
            st.session_state.last_heartbeat[agent_name] = datetime.now().strftime("%H:%M:%S")
            time.sleep(0.5)
            continue

        # Execute task with simulated progress
        task_steps = 20
        for step in range(1, task_steps + 1):
            try:
                result = task(step, task_steps)
                st.session_state.agent_progress[agent_name] = step / task_steps
                st.session_state.last_heartbeat[agent_name] = datetime.now().strftime("%H:%M:%S")
                time.sleep(0.1)
            except Exception as e:
                st.session_state.agent_logs[agent_name].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Task failed: {e}"
                )
                st.session_state.agent_progress[agent_name] = 0.0
                break
        else:
            st.session_state.agent_logs[agent_name].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] Task completed successfully"
            )
            st.session_state.agent_progress[agent_name] = 0.0


def heartbeat_status(agent_name):
    """Return a colored emoji representing agent heartbeat freshness"""
    last_seen = st.session_state.last_heartbeat.get(agent_name)
    status = st.session_state.agent_status.get(agent_name, "idle")

    if status == "running":
        if last_seen:
            last_time = datetime.strptime(last_seen, "%H:%M:%S")
            delta = (datetime.now() - last_time).total_seconds()
            if delta <= 1:
                return "💚"
            elif delta <= 2:
                return "💛"
            else:
                return "🟡"
        else:
            return "💚"
    elif status == "stopped":
        return "🔴"
    else:
        return "🟡"


# --- Sidebar Controls ---
st.title("🧠 Agent Dashboard")
st.sidebar.header("Controls")

selected_agent = st.sidebar.selectbox("Select Agent", agents)

col1, col2 = st.sidebar.columns(2)
with col1:
    start_clicked = st.button("▶ Start")
with col2:
    stop_clicked = st.button("⏹ Stop")

# --- Task Function Selection ---
st.sidebar.markdown("---")
st.sidebar.subheader("Submit Task")
task_type = st.sidebar.selectbox(
    "Function",
    ["Translate Text", "Summarize Text", "Spellcheck Text", "Translate Document"]
)

# Conditional input fields
task_input = None
uploaded_file = None

if task_type in ["Translate Text", "Summarize Text", "Spellcheck Text"]:
    task_input = st.sidebar.text_area(f"Enter text for {task_type}")

if task_type == "Translate Document":
    uploaded_file = st.sidebar.file_uploader("Upload document (.txt only)", type=["txt"])

submit_task = st.sidebar.button("Submit Task")

auto_refresh = st.sidebar.checkbox("Live updates", value=True)

# --- Handle Start / Stop ---
timestamp = datetime.now().strftime("%H:%M:%S")

if start_clicked:
    if st.session_state.agent_status[selected_agent] != "running":
        st.session_state.agent_status[selected_agent] = "running"
        st.session_state.agent_logs[selected_agent].append(
            f"[{timestamp}] Agent started"
        )
        thread = threading.Thread(
            target=agent_worker,
            args=(selected_agent,),
            daemon=True
        )
        st.session_state.agent_threads[selected_agent] = thread
        thread.start()

if stop_clicked:
    if st.session_state.agent_status[selected_agent] == "running":
        st.session_state.agent_status[selected_agent] = "stopped"
        st.session_state.agent_logs[selected_agent].append(
            f"[{timestamp}] Agent stopped"
        )

# --- Handle Task Submission ---
if submit_task:
    if (task_input and task_input.strip()) or uploaded_file:
        def make_task(task_type, content):
            def task(step, total_steps):
                time.sleep(0.05)  # simulate work step
                # For documents, show first 50 chars
                display_content = content if isinstance(content, str) else content[:50]
                return f"{task_type}: {display_content}... step {step}/{total_steps}"
            return task

        # Read uploaded file
        if uploaded_file:
            file_content = uploaded_file.read().decode("utf-8")
            content = file_content
        else:
            content = task_input

        st.session_state.agent_queues[selected_agent].put(make_task(task_type, content))
        st.session_state.agent_logs[selected_agent].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Task queued: {task_type}"
        )
        st.experimental_rerun()

# --- Display Status & Logs ---
st.subheader("Agent Status & Logs")

for agent, status in st.session_state.agent_status.items():
    last_seen = st.session_state.last_heartbeat[agent]
    pulse = heartbeat_status(agent)
    queue_size = st.session_state.agent_queues[agent].qsize()
    header_text = f"{pulse} {agent} — {status.upper()} (Queue: {queue_size})"
    if last_seen:
        header_text += f" (Last heartbeat: {last_seen})"

    with st.expander(header_text):
        # Show progress bar
        progress = st.session_state.agent_progress[agent]
        st.progress(progress)

        # Show last 10 logs
        logs = st.session_state.agent_logs[agent]
        if logs:
            for line in logs[-10:]:
                st.text(line)
        else:
            st.text("No logs yet.")

# --- Auto-refresh for live updates ---
if auto_refresh:
    time.sleep(0.5)
    st.rerun()
