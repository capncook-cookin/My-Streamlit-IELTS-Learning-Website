"""
IELTS Practice Web App — starter scaffold
--------------------------------------------
Run locally with:
    pip install streamlit
    streamlit run app.py

This gives you a working website (Streamlit serves it in the browser)
with three modules:
  1. Reading practice (auto-graded multiple choice)
  2. Writing practice (heuristic feedback -> swap for AI grading later)
  3. Progress tracker (session history + simple chart)

Everything is in one file on purpose, so it's easy to read end-to-end.
Once you're comfortable, split into modules: data.py, reading.py, writing.py, etc.
"""

import streamlit as st
import json
import os
import re
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIG / PERSISTENCE
# ---------------------------------------------------------------------------
DATA_FILE = "ielts_progress.json"

def load_progress():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"reading": [], "writing": []}

def save_progress(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

if "progress" not in st.session_state:
    st.session_state.progress = load_progress()

# ---------------------------------------------------------------------------
# SAMPLE CONTENT — replace/expand with a real question bank
# TODO: move this into a separate questions.json or a database once you
# have more than a handful of passages.
# ---------------------------------------------------------------------------
READING_PASSAGES = [
    {
        "id": "r1",
        "title": "The Rise of Urban Beekeeping",
        "text": (
            "Over the past decade, city dwellers across the world have taken up "
            "beekeeping as a hobby and, increasingly, as a small business. Rooftops "
            "in cities such as London, New York and Tokyo now host thousands of "
            "hives. Proponents argue that urban bees are often healthier than their "
            "rural counterparts, since cities tend to have a greater diversity of "
            "flowering plants and lower pesticide use than industrial farmland. "
            "Critics, however, warn that packing too many hives into a small area "
            "can lead to competition for nectar, potentially harming wild pollinator "
            "populations that were already under pressure."
        ),
        "questions": [
            {
                "q": "According to the passage, why might urban bees be healthier than rural bees?",
                "options": [
                    "Cities have fewer flowering plants",
                    "Cities often have lower pesticide use and more plant diversity",
                    "Urban beekeepers use more medication",
                    "Rural areas have more predators",
                ],
                "answer": 1,
            },
            {
                "q": "What concern do critics raise about urban beekeeping?",
                "options": [
                    "It is too expensive",
                    "It requires too much space",
                    "Too many hives may compete with wild pollinators",
                    "Honey quality is lower in cities",
                ],
                "answer": 2,
            },
        ],
    },
]

WRITING_PROMPTS = [
    "Some people believe that unpaid community service should be a "
    "compulsory part of high school education. To what extent do you agree "
    "or disagree?",
    "The chart below shows the percentage of households with internet "
    "access in three countries between 2000 and 2020. Summarise the "
    "information by selecting and reporting the main features.",
]

# ---------------------------------------------------------------------------
# WRITING FEEDBACK — heuristic placeholder
# TODO: replace this function with a real grader. Options:
#   - Call an LLM API (OpenAI/Anthropic) with a rubric-based prompt
#   - Use a grammar-checking library (e.g. language_tool_python)
#   - Train/fine-tune a small model on public IELTS-scored essay datasets
# Keep the return shape the same ({"band_estimate": float, "notes": [...]})
# so the UI code below doesn't need to change when you swap this out.
# ---------------------------------------------------------------------------
def heuristic_writing_feedback(essay: str, task_type: str = "task2") -> dict:
    words = re.findall(r"\b\w+\b", essay)
    word_count = len(words)
    sentences = re.split(r"[.!?]+", essay)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)
    avg_sentence_len = word_count / sentence_count if sentence_count else 0

    notes = []
    min_words = 250 if task_type == "task2" else 150
    if word_count < min_words:
        notes.append(f"Word count is {word_count}; aim for at least {min_words}.")
    else:
        notes.append(f"Word count OK ({word_count} words).")

    if avg_sentence_len < 8:
        notes.append("Sentences look short/simple on average — try combining ideas with linking words (however, although, whereas).")
    elif avg_sentence_len > 30:
        notes.append("Average sentence length is very high — check for run-on sentences.")
    else:
        notes.append("Sentence length variation looks reasonable.")

    linking_words = ["however", "therefore", "furthermore", "moreover", "in contrast",
                      "as a result", "for example", "in addition", "on the other hand"]
    used_links = [w for w in linking_words if w in essay.lower()]
    if len(used_links) >= 2:
        notes.append(f"Good use of cohesive devices ({', '.join(used_links)}).")
    else:
        notes.append("Try using more linking phrases to improve coherence/cohesion.")

    # Extremely rough band estimate — NOT a real IELTS score.
    # This is only here so the UI has something to display; replace with
    # real scoring logic before relying on it.
    band_estimate = 5.0
    if word_count >= min_words:
        band_estimate += 0.5
    if 8 <= avg_sentence_len <= 30:
        band_estimate += 0.5
    if len(used_links) >= 2:
        band_estimate += 1.0
    band_estimate = min(band_estimate, 8.0)

    return {"band_estimate": round(band_estimate, 1), "notes": notes,
            "word_count": word_count, "sentence_count": sentence_count}

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="IELTS Practice", page_icon="📝", layout="centered")

st.sidebar.title("IELTS Practice")
page = st.sidebar.radio("Go to", ["Home", "Reading Practice", "Writing Practice", "Progress"])

# ---------------- HOME ----------------
if page == "Home":
    st.title("📝 IELTS Practice App")
    st.write(
        "A lightweight practice tool. Start with Reading or Writing from the "
        "sidebar. Your scores are saved locally so you can track progress "
        "over time."
    )
    st.info("This is a starter scaffold — heuristic writing feedback is a placeholder. "
            "See the TODO comments in app.py for where to plug in real grading logic.")

# ---------------- READING ----------------
elif page == "Reading Practice":
    st.title("📖 Reading Practice")
    passage = READING_PASSAGES[0]  # TODO: let user pick from multiple passages
    st.subheader(passage["title"])
    st.write(passage["text"])
    st.divider()

    answers = {}
    for i, q in enumerate(passage["questions"]):
        st.markdown(f"**Q{i+1}. {q['q']}**")
        answers[i] = st.radio("", q["options"], key=f"q_{i}", index=None, label_visibility="collapsed")

    if st.button("Submit Answers"):
        correct = 0
        for i, q in enumerate(passage["questions"]):
            if answers[i] == q["options"][q["answer"]]:
                correct += 1
        total = len(passage["questions"])
        st.success(f"Score: {correct}/{total}")

        st.session_state.progress["reading"].append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "passage_id": passage["id"],
            "score": correct,
            "total": total,
        })
        save_progress(st.session_state.progress)

# ---------------- WRITING ----------------
elif page == "Writing Practice":
    st.title("✍️ Writing Practice")
    prompt = st.selectbox("Choose a prompt", WRITING_PROMPTS)
    st.write(f"**Prompt:** {prompt}")

    essay = st.text_area("Write your response here", height=300)

    if st.button("Get Feedback"):
        if not essay.strip():
            st.warning("Write something first!")
        else:
            with st.spinner("Analyzing..."):
                time.sleep(0.5)  # cosmetic; remove once real API calls add their own latency
                result = heuristic_writing_feedback(essay)

            st.metric("Estimated Band (rough placeholder)", result["band_estimate"])
            st.write(f"Word count: {result['word_count']} | Sentences: {result['sentence_count']}")
            st.subheader("Notes")
            for note in result["notes"]:
                st.write(f"- {note}")

            st.session_state.progress["writing"].append({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "word_count": result["word_count"],
                "band_estimate": result["band_estimate"],
            })
            save_progress(st.session_state.progress)

# ---------------- PROGRESS ----------------
elif page == "Progress":
    st.title("📊 Your Progress")

    reading_data = st.session_state.progress["reading"]
    writing_data = st.session_state.progress["writing"]

    if reading_data:
        st.subheader("Reading scores over time")
        scores = [r["score"] / r["total"] * 100 for r in reading_data]
        st.line_chart(scores)
        st.write(f"Attempts: {len(reading_data)} | Latest: {scores[-1]:.0f}%")
    else:
        st.write("No reading attempts yet.")

    if writing_data:
        st.subheader("Writing band estimates over time")
        bands = [w["band_estimate"] for w in writing_data]
        st.line_chart(bands)
        st.write(f"Attempts: {len(writing_data)} | Latest estimate: {bands[-1]}")
    else:
        st.write("No writing attempts yet.")

    if reading_data or writing_data:
        if st.button("Clear all progress"):
            st.session_state.progress = {"reading": [], "writing": []}
            save_progress(st.session_state.progress)
            st.rerun()wwwwwwwwwwwwwwwww
