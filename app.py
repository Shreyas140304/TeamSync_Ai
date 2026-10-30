import streamlit as st
from datetime import date

from database import (
    init_db,
    save_meeting,
    get_all_tasks,
    update_task_status,
    update_task_owner,
)

from ai_service import analyze_meeting
from rag import answer_question
from handover import generate_handover_brief


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="TeamSync AI",
    page_icon="📋",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(ellipse at 12% 0%, #edf4ff 0, transparent 34%),
            #f6f8fc;
    }
    .block-container {
        max-width: 1380px;
        padding: 2rem 2.5rem 3rem;
    }
    [data-testid="stHeader"] {
        background: transparent;
    }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e6eaf2;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 4px 16px rgba(27, 45, 80, 0.04);
    }
    [data-testid="stMetricLabel"] {
        color: #64748b;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.45rem;
        border-bottom: 1px solid #e4e9f2;
        padding-bottom: 0.35rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0 1rem;
        border-radius: 10px 10px 0 0;
        color: #64748b;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #315ee8;
        border-bottom-color: #315ee8;
    }
    div[data-testid="stForm"] {
        background: #ffffff;
        border: 1px solid #e6eaf2;
        border-radius: 14px;
        padding: 1.25rem;
    }
    div[data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid #e6eaf2;
        border-radius: 12px;
        margin-bottom: 0.65rem;
    }
    .dashboard-subtitle {
        color: #64748b;
        margin-top: -0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize database
init_db()


# --------------------------------------------------
# HEADER
# --------------------------------------------------

brand, tagline = st.columns([1.2, 2.8], vertical_alignment="center")
with brand:
    st.markdown("## 📋 TeamSync AI")
with tagline:
    st.markdown(
        '<p class="dashboard-subtitle">'
        "Meeting intelligence, team tasks, and shared knowledge — in one place."
        "</p>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
# NAVIGATION TABS
# --------------------------------------------------

tab0, tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🏠 Overview",
        "📝 Meeting Intelligence",
        "✅ Task Management",
        "🔍 Knowledge Base",
        "🤝 Smart Handover",
    ]
)


# ==================================================
# TAB 0: DASHBOARD OVERVIEW
# ==================================================

with tab0:
    tasks = get_all_tasks()
    open_count = sum(
        task["status"] in ("Open", "In Progress")
        for task in tasks
    )
    completed_count = sum(
        task["status"] == "Completed"
        for task in tasks
    )
    assigned_owners = {
        task["owner"].strip().casefold()
        for task in tasks
        if task["owner"] and task["owner"].strip()
    }

    st.subheader("Team overview")
    st.markdown(
        '<p class="dashboard-subtitle">'
        "A quick view of your team's action items and progress."
        "</p>",
        unsafe_allow_html=True,
    )

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Total action items", len(tasks))
    metric2.metric("Open / in progress", open_count)
    metric3.metric("Completed", completed_count)
    metric4.metric("Assigned teammates", len(assigned_owners))

    st.markdown("### Recent action items")
    if tasks:
        recent_tasks = [
            {
                "Task": task["description"],
                "Owner": task["owner"] or "Unassigned",
                "Status": task["status"],
                "Meeting": task["meeting_title"],
                "Due date": task["due_date"] or "Not specified",
            }
            for task in tasks[:6]
        ]
        st.dataframe(
            recent_tasks,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info(
            "No action items yet. Start by analyzing your first meeting."
        )


# ==================================================
# TAB 1: MEETING INTELLIGENCE
# ==================================================

with tab1:
    st.header("Meeting Intelligence")

    st.write(
        "Enter meeting details and let Gemini extract "
        "summaries, decisions, and action items."
    )

    with st.form("meeting_form"):
        title = st.text_input(
            "Meeting Title",
            placeholder="e.g. Website Launch Planning",
        )

        date_column, participants_column = st.columns(2)
        with date_column:
            meeting_date = st.date_input(
                "Meeting Date",
                value=date.today(),
            )
        with participants_column:
            participants = st.text_input(
                "Participants",
                placeholder="e.g. Rahul, Priya, Amit",
            )

        notes = st.text_area(
            "Meeting Notes",
            height=250,
            placeholder=(
                "Paste your meeting notes here...\n"
                "- Discussed project deadlines\n"
                "- Rahul will complete testing\n"
                "- Launch planned after approval"
            ),
        )

        submitted = st.form_submit_button(
            "✨ Analyze Meeting",
            use_container_width=True,
        )

    if submitted:
        if not title.strip():
            st.error("Please enter a meeting title.")

        elif not notes.strip():
            st.error("Please enter meeting notes.")

        else:
            try:
                with st.spinner(
                    "Gemini is analyzing your meeting..."
                ):
                    analysis = analyze_meeting(
                        title,
                        participants,
                        notes,
                    )

                st.session_state["meeting_analysis"] = analysis
                st.session_state["meeting_details"] = {
                    "title": title.strip(),
                    "meeting_date": meeting_date.isoformat(),
                    "participants": participants.strip(),
                    "notes": notes.strip(),
                }

            except Exception:
                st.error(
                    "Meeting analysis failed. Check your API "
                    "configuration and application logs."
                )

    # Display the analysis
    analysis = st.session_state.get("meeting_analysis")

    if analysis is not None:
        st.subheader("📊 Analysis Results")

        summary_column, decisions_column = st.columns(2)
        with summary_column:
            with st.container(border=True):
                st.markdown("#### Summary")
                st.write(analysis.summary)
        with decisions_column:
            with st.container(border=True):
                st.markdown("#### Decisions")
                if analysis.decisions:
                    for decision in analysis.decisions:
                        st.markdown(f"- {decision}")
                else:
                    st.info("No explicit decisions were identified.")

        st.markdown("#### Action items")
        if analysis.action_items:
            action_rows = [
                {
                    "Task": item.description,
                    "Owner": item.owner or "Unassigned",
                    "Due date": item.due_date or "Not specified",
                }
                for item in analysis.action_items
            ]
            st.dataframe(
                action_rows,
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No action items were identified.")

        if st.button(
            "💾 Save Meeting and Tasks",
            use_container_width=True,
        ):
            try:
                details = st.session_state["meeting_details"]

                meeting_id = save_meeting(
                    details["title"],
                    details["meeting_date"],
                    details["participants"],
                    details["notes"],
                    analysis,
                )

                st.success(
                    f"Meeting and action items saved successfully! "
                    f"Meeting ID: {meeting_id}"
                )

                del st.session_state["meeting_analysis"]
                del st.session_state["meeting_details"]

            except Exception:
                st.error(
                    "Could not save the meeting. "
                    "Check the application logs."
                )


# ==================================================
# TAB 2: TASK MANAGEMENT
# ==================================================

with tab2:
    st.header("Task Management")

    st.write(
        "Track action items, update statuses, and record outcomes."
    )

    tasks = get_all_tasks()

    if not tasks:
        st.info(
            "No tasks found. Analyze and save a meeting first."
        )

    else:
        status_options = [
            "Open",
            "In Progress",
            "Completed",
            "Carried Forward",
        ]

        for task in tasks:
            with st.expander(
                f"Task #{task['id']}: {task['description']}"
            ):
                meeting_column, due_column, owner_column = st.columns(3)
                meeting_column.caption("MEETING")
                meeting_column.write(task["meeting_title"])
                due_column.caption("DUE DATE")
                due_column.write(task["due_date"] or "Not specified")
                owner_column.caption("CURRENT OWNER")
                owner_column.write(task["owner"] or "Unassigned")

                owner_input, owner_button = st.columns([3, 1])
                with owner_input:
                    owner = st.text_input(
                        "Assigned owner",
                        value=task["owner"] or "",
                        placeholder="Leave blank to mark unassigned",
                        key=f"owner_{task['id']}",
                    )
                with owner_button:
                    st.write("")
                    save_owner = st.button(
                        "Save owner",
                        key=f"save_owner_{task['id']}",
                        use_container_width=True,
                    )

                if save_owner:
                    try:
                        update_task_owner(task["id"], owner)
                        st.session_state[
                            f"owner_saved_{task['id']}"
                        ] = True
                        st.rerun()

                    except Exception:
                        st.error(
                            "Could not update the task owner. "
                            "Check the application logs."
                        )

                if st.session_state.pop(
                    f"owner_saved_{task['id']}", False
                ):
                    st.success("Task owner updated successfully.")

                status_column, outcome_column = st.columns(2)
                with status_column:
                    current_status = task["status"]
                    new_status = st.selectbox(
                        "Update status",
                        status_options,
                        index=(
                            status_options.index(current_status)
                            if current_status in status_options
                            else 0
                        ),
                        key=f"status_{task['id']}",
                    )
                with outcome_column:
                    outcome = st.text_input(
                        "Outcome or completion notes",
                        value=task["outcome"] or "",
                        key=f"outcome_{task['id']}",
                    )

                if st.button(
                    "Save Changes",
                    key=f"save_{task['id']}",
                    use_container_width=True,
                ):
                    try:
                        update_task_status(
                            task["id"],
                            new_status,
                            outcome,
                        )

                        st.success("Task updated successfully.")
                        st.rerun()

                    except Exception:
                        st.error(
                            "Could not update this task. "
                            "Check the application logs."
                        )


# ==================================================
# TAB 3: KNOWLEDGE BASE / RAG
# ==================================================

with tab3:
    st.header("Knowledge base")

    st.write(
        "Ask questions about previous meetings, decisions, "
        "and project discussions."
    )

    with st.container(border=True):
        question = st.text_area(
            "Ask a question",
            placeholder=(
                "Example: What decisions were made about the website launch?"
            ),
            height=120,
        )

        search_clicked = st.button(
            "🔍 Search team knowledge",
            use_container_width=True,
        )

    if search_clicked:
        if not question.strip():
            st.warning("Please enter a question.")

        else:
            try:
                with st.spinner(
                    "Searching meeting history and generating an answer..."
                ):
                    answer = answer_question(question)

                st.subheader("Answer")
                with st.container(border=True):
                    st.markdown(answer)

            except Exception:
                st.error(
                    "Could not generate an answer. "
                    "Check your API configuration and logs."
                )


# ==================================================
# TAB 4: SMART HANDOVER
# ==================================================

with tab4:
    st.header("Smart handover")

    st.write(
        "Generate a personalized catch-up brief using a teammate's "
        "open tasks and relevant meeting history."
    )

    owner_column, generate_column = st.columns([2, 1])
    with owner_column:
        owner = st.text_input(
            "Teammate name",
            placeholder="e.g. Rahul",
        )
    with generate_column:
        st.write("")
        generate_clicked = st.button(
            "🤝 Generate handover brief",
            use_container_width=True,
        )

    if generate_clicked:
        if not owner.strip():
            st.warning("Please enter a teammate's name.")

        else:
            try:
                with st.spinner(
                    "Generating the handover brief..."
                ):
                    brief = generate_handover_brief(
                        owner.strip()
                    )

                st.subheader("Your Handover Brief")
                with st.container(border=True):
                    st.markdown(brief)

            except Exception:
                st.error(
                    "Could not generate the handover brief. "
                    "Check your API configuration and logs."
                )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

footer_left, footer_right = st.columns([2, 1])
with footer_left:
    st.caption(
        "TeamSync AI · Meeting intelligence · Task management · Team knowledge"
    )
with footer_right:
    st.caption("Built for teams that stay in sync.")