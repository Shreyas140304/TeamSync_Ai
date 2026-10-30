from database import (
    get_connection,
    carry_forward_task,
)

with get_connection() as conn:
    meetings = conn.execute(
        "SELECT id, title FROM meetings ORDER BY id"
    ).fetchall()

    tasks = conn.execute(
        """
        SELECT id, description, status, meeting_id
        FROM action_items
        ORDER BY id
        """
    ).fetchall()

print("Meetings:")
for meeting in meetings:
    print(dict(meeting))

print("\nTasks:")
for task in tasks:
    print(dict(task))

# new_task_id = carry_forward_task(
#     task_id=2,
#     new_meeting_id=2
# )

# print("New task created:", new_task_id)