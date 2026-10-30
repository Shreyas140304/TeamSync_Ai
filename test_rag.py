import streamlit as st

from rag import answer_question, retrieve_relevant_meetings

st.title("TeamSync AI — Meeting Knowledge Search")

question = st.text_input(
    "Ask about previous meetings",
    placeholder="Why was the website launch delayed?"
)

if st.button("Search Meetings"):

    try:
        with st.spinner("Searching meeting history..."):

            results = retrieve_relevant_meetings(question)

            st.subheader("Retrieved Meetings")

            for result in results:
                st.write(
                    f"Meeting #{result['meeting_id']}: "
                    f"{result['title']}"
                )
                st.write(
                    f"Similarity: {result['similarity']:.3f}"
                )
                st.write("---")

            answer = answer_question(question)

        st.subheader("AI Answer")
        st.write(answer)

    except Exception as exc:
        st.error(f"Search failed: {exc}")