import streamlit as st
from ai_service import analyze_meeting

st.title("Test Gemini Meeting Analysis")

title = st.text_input("Meeting title", "Website Launch")
participants = st.text_input("Participants", "Priya, Rahul")

notes = st.text_area(
    "Meeting notes",
    "Priya will finish the homepage by November 5. "
    "Rahul will test the payment system by November 7. "
    "The team decided to launch after testing is complete."
)

if st.button("Analyze Meeting"):
    try:
        result = analyze_meeting(title, participants, notes)
        st.subheader("Summary")
        st.write(result.summary)

        st.subheader("Decisions")
        st.write(result.decisions)

        st.subheader("Action Items")
        st.json(
            [item.model_dump() for item in result.action_items]
        )

        st.subheader("Risks")
        st.write(result.risks)

    except Exception as exc:
        st.error(f"Analysis failed: {exc}")