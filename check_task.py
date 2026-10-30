from database import get_connection

with get_connection() as conn:
    rows = conn.execute("""
        SELECT
            id,
            description,
            owner,
            status,
            meeting_id
        FROM action_items
    """).fetchall()

    for row in rows:
        print(dict(row))