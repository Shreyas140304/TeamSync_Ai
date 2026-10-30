import streamlit as st

from database import (
    init_db,
    get_all_tasks,
    update_task_status,
)
from handover import generate_handover_brief

init_db()

st.title("TeamSync AI")
st.caption("Meeting Intelligence and Task Management")

tab1, tab2 = st.tabs(["Task Management", "Smart Handover"])

# -------------------------------
# Tab 1: Task Management
# -------------------------------
with tab1:
    st.subheader("All Action Items")

    tasks = get_all_tasks()

    if not tasks:
        st.info("No tasks found. Analyze and save a meeting first.")
    else:
        for task in tasks:
            with st.expander(
                f"Task #{task['id']}: {task['description']}"
            ):
                st.write(f"Meeting: {task['meeting_title']}")
                st.write(f"Owner: {task['owner'] or 'Unassigned'}")
                st.write(f"Due date: {task['due_date'] or 'Not specified'}")
                st.write(f"Current status: {task['status']}")

                status_options = [
                    "Open",
                    "In Progress",
                    "Completed",
                    "Carried Forward",
                ]

                current_status = task["status"]

                new_status = st.selectbox(
                    "Update status",
                    status_options,
                    index=(
                        status_options.index(current_status)
                        if current_status in status_options
                        else 0
                    ),
                    key=f"status_{task['id']}"
                )

                outcome = st.text_input(
                    "Outcome or completion notes",
                    value=task["outcome"] or "",
                    key=f"outcome_{task['id']}"
                )

                if st.button(
                    "Save Changes",
                    key=f"save_{task['id']}"
                ):
                    update_task_status(
                        task["id"],
                        new_status,
                        outcome
                    )

                    st.success("Task updated.")
                    st.rerun()

# -------------------------------
# Tab 2: Smart Handover
# -------------------------------
with tab2:
    st.subheader("Generate a Handover Brief")

    owner = st.text_input(
        "Teammate's name",
        placeholder="e.g. Priya"
    )

    if st.button("Generate Brief"):
        try:
            with st.spinner("Preparing handover brief..."):
                brief = generate_handover_brief(owner)

            st.markdown(brief)

        except Exception as exc:
            st.error(f"Could not generate brief: {exc}")