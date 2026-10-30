import streamlit as st
import numpy as np
import faiss
import time
import time
from uuid import uuid4
from logging_config import log_event
from logging_config import log_event
from sentence_transformers import SentenceTransformer
from google import genai

from database import get_connection


# 1. Load the embedding model
embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


# 2. Retrieve meeting records from SQLite
def get_meetings():

    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT id, title, meeting_date, participants,
                   raw_notes, summary, decisions
            FROM meetings
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


# 3. Convert each meeting into searchable text
def prepare_meeting_text(meeting):

    return f"""
    Meeting title: {meeting['title']}
    Date: {meeting['meeting_date']}
    Participants: {meeting['participants'] or 'Not specified'}
    Summary: {meeting['summary'] or ''}
    Decisions: {meeting['decisions'] or ''}
    Original notes: {meeting['raw_notes']}
    """


# 4. Build the FAISS index
def build_index(meetings):

    if not meetings:
        return None, None

    documents = [
        prepare_meeting_text(meeting)
        for meeting in meetings
    ]

    embeddings = embedding_model.encode(
        documents,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embeddings = embeddings.astype("float32")

    # Inner product of normalized vectors gives cosine similarity
    index = faiss.IndexFlatIP(embeddings.shape[1])

    index.add(embeddings)

    return index, documents


# 5. Retrieve the most relevant meetings
def retrieve_relevant_meetings(question, top_k=3):

    meetings = get_meetings()

    if not meetings:
        return []

    index, documents = build_index(meetings)

    query_embedding = embedding_model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    k = min(top_k, len(meetings))

    scores, indices = index.search(query_embedding, k)

    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx == -1:
            continue

        results.append({
            "meeting_id": meetings[idx]["id"],
            "title": meetings[idx]["title"],
            "similarity": float(score),
            "content": documents[idx]
        })

    return results


# 6. Generate an answer using retrieved evidence
def answer_question(question):
    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    request_id = str(uuid4())[:8]
    start_time = time.perf_counter()

    log_event(
        "info",
        "rag_answer_started",
        request_id=request_id,
    )

    try:
        retrieved = retrieve_relevant_meetings(question)

        log_event(
            "info",
            "rag_retrieval_completed",
            request_id=request_id,
            retrieved_count=len(retrieved),
        )

        if not retrieved:
            return (
                "I couldn't find any meeting records to answer this question. "
                "Please save a meeting first."
            )

        context = "\n\n".join(
            f"Meeting ID: {item['meeting_id']}\n"
            f"Title: {item['title']}\n"
            f"Similarity score: {item['similarity']:.3f}\n"
            f"{item['content']}"
            for item in retrieved
        )

        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key is not configured.")

        client = genai.Client(api_key=api_key)

        prompt = f"""
        You are TeamSync AI, a meeting knowledge assistant.

        Answer the user's question using the meeting records below.

        Rules:
        - Base factual claims on the supplied records.
        - Do not invent decisions, deadlines, or events.
        - If the records do not contain enough information, say so.
        - Distinguish recorded facts from reasonable interpretations.
        - Mention relevant meeting titles when useful.

        MEETING RECORDS:
        {context}

        USER QUESTION:
        {question}
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        if not response.text:
            raise ValueError("Gemini returned an empty answer.")

        latency_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        log_event(
            "info",
            "rag_answer_succeeded",
            request_id=request_id,
            latency_ms=latency_ms,
            retrieved_count=len(retrieved),
        )

        return response.text

    except Exception as exc:
        latency_ms = round(
            (time.perf_counter() - start_time) * 1000, 2
        )

        log_event(
            "error",
            "rag_answer_failed",
            request_id=request_id,
            latency_ms=latency_ms,
            error_type=type(exc).__name__,
        )
        raise