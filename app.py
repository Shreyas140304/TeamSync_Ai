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

# Initialize database
init_db()


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.title("📋 TeamSync AI")

st.markdown(
    """
    **AI-powered meeting intelligence and task management**

    Turn meeting discussions into actionable tasks, preserve team knowledge,
    and generate personalized handover briefs.
    """
)

st.divider()


# --------------------------------------------------
# NAVIGATION TABS
# --------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "📝 Meeting Intelligence",
        "✅ Task Management",
        "🔍 Knowledge Base",
        "🤝 Smart Handover",
    ]
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

        meeting_date = st.date_input(
            "Meeting Date",
            value=date.today(),
        )

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

        st.markdown("### Summary")
        st.write(analysis.summary)

        st.markdown("### Decisions")

        if analysis.decisions:
            for decision in analysis.decisions:
                st.markdown(f"- {decision}")
        else:
            st.info("No explicit decisions were identified.")

        st.markdown("### Action Items")

        if analysis.action_items:
            for item in analysis.action_items:
                st.markdown(
                    f"- **Task:** {item.description}\n"
                    f"  - **Owner:** {item.owner or 'Unassigned'}\n"
                    f"  - **Due date:** {item.due_date or 'Not specified'}"
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
                st.write(
                    f"**Meeting:** {task['meeting_title']}"
                )

                st.write(
                    f"**Owner:** {task['owner'] or 'Unassigned'}"
                )

                owner = st.text_input(
                    "Assigned owner",
                    value=task["owner"] or "",
                    placeholder="Leave blank to mark unassigned",
                    key=f"owner_{task['id']}",
                )

                if st.button(
                    "Save Owner",
                    key=f"save_owner_{task['id']}",
                ):
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

                st.write(
                    f"**Due date:** {task['due_date'] or 'Not specified'}"
                )

                st.write(
                    f"**Current status:** {task['status']}"
                )

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

                outcome = st.text_input(
                    "Outcome or completion notes",
                    value=task["outcome"] or "",
                    key=f"outcome_{task['id']}",
                )

                if st.button(
                    "Save Changes",
                    key=f"save_{task['id']}",
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
    st.header("Team Knowledge Base")

    st.write(
        "Ask questions about previous meetings, decisions, "
        "and project discussions."
    )

    question = st.text_area(
        "Ask a question",
        placeholder=(
            "Example: What decisions were made about the website launch?"
        ),
        height=100,
    )

    if st.button(
        "🔍 Search Team Knowledge",
        use_container_width=True,
    ):
        if not question.strip():
            st.warning("Please enter a question.")

        else:
            try:
                with st.spinner(
                    "Searching meeting history and generating an answer..."
                ):
                    answer = answer_question(question)

                st.subheader("Answer")
                st.write(answer)

            except Exception:
                st.error(
                    "Could not generate an answer. "
                    "Check your API configuration and logs."
                )


# ==================================================
# TAB 4: SMART HANDOVER
# ==================================================

with tab4:
    st.header("Smart Handover Brief")

    st.write(
        "Generate a personalized catch-up brief using a teammate's "
        "open tasks and relevant meeting history."
    )

    owner = st.text_input(
        "Teammate Name",
        placeholder="e.g. Rahul",
    )

    if st.button(
        "🤝 Generate Handover Brief",
        use_container_width=True,
    ):
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

st.caption(
    "TeamSync AI | Meeting Intelligence • Task Management • RAG • Smart Handover"
)