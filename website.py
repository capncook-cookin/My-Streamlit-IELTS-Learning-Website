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

from dotenv import load_dotenv
import streamlit as st
import json
import os
import re
import requests
from datetime import datetime

# Load environment variables from .env (auto-fills the Groq API key).
load_dotenv()

# ---------------------------------------------------------------------------
# CHATBOT CONFIG — powered by Groq's free API (hosts open-source models
# like Llama 3.3). Get a free key at https://console.groq.com/keys
# Do NOT hardcode your key in this file if you ever push it to GitHub —
# use an environment variable instead (see instructions below the code).
# ---------------------------------------------------------------------------
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"  # open-source model hosted by Groq

def ask_explainer_bot(question, user_answer, correct_answer, api_key):
    """
    Sends the question/answer pair to the chatbot and asks for a short
    explanation of why the correct answer is correct. Returns the model's
    reply as a string, or an error message string if something went wrong.
    """
    system_prompt = (
        "You are an IELTS tutor. A student got a practice question wrong "
        "or wants to understand it better. Explain briefly (under 300 words) "
        "why the correct answer is correct, and if relevant, why the "
        "student's answer was wrong. Be encouraging and clear, not harsh."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"Student's answer: {user_answer}\n"
        f"Correct answer: {correct_answer}\n\n"
        "Explain why the correct answer is right."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.4,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            return "⚠️ Invalid API key. Double-check you pasted it correctly."
        return f"⚠️ API error: {e}"
    except requests.exceptions.RequestException as e:
        return f"⚠️ Network error: {e}"

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

# Auto-fill the Groq API key from .env on first launch. The user can still
# override it in the top-bar input below; the app never writes the key to disk.
if "groq_api_key" not in st.session_state:
    env_key = os.getenv("GROQ_API_KEY")
    if env_key:
        st.session_state["groq_api_key"] = env_key

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
    if 8 <= avg_sentence_len <= 25:
        band_estimate += 0.5
    if len(used_links) >= 2:
        band_estimate += 1.0
    band_estimate = min(band_estimate, 8.0)

    return {"band_estimate": round(band_estimate, 1), "notes": notes,
            "word_count": word_count, "sentence_count": sentence_count}

# ---------------------------------------------------------------------------
# REAL AI WRITING GRADING — replaces the heuristic placeholder when an API
# key is available. Grades against the four official IELTS writing criteria.
# ---------------------------------------------------------------------------
def ai_writing_feedback(essay: str, prompt: str, api_key: str) -> dict:
    system_prompt = (
        "You are an official IELTS Writing examiner. Grade the essay against "
        "the four IELTS band criteria: Task Achievement, Coherence & Cohesion, "
        "Lexical Resource, and Grammatical Range & Accuracy. "
        "Respond ONLY in raw JSON, no markdown fences, no preamble, in this "
        "exact shape: "
        '{"band_estimate": <number 1-9, one decimal place>, '
        '"task_achievement_band": <number 1-9, one decimal place>, '
        '"coherence_cohesion_band": <number 1-9, one decimal place>, '
        '"lexical_resource_band": <number 1-9, one decimal place>, '
        '"grammar_band": <number 1-9, one decimal place>, '
        '"task_achievement": "<one sentence>", "coherence_cohesion": "<one sentence>", '
        '"lexical_resource": "<one sentence>", "grammar": "<one sentence>", '
        '"overall_tip": "<one sentence, the single most useful thing to fix next>"}'
    )
    user_prompt = f"Prompt: {prompt}\n\nEssay:\n{essay}"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.3,
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        # Model sometimes wraps JSON in code fences despite instructions — strip them.
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(raw)
        return parsed
    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# COACH — diagnosis + proactive suggestion, the piece that ties every
# skill's history together into one "what should I do next" signal.
# `diagnose()` is the lightweight snapshot used on the Home page.
# `coach_detail()` is the deeper view for the dedicated Coach page.
# ---------------------------------------------------------------------------
def diagnose(progress: dict) -> dict:
    reading = progress.get("reading", [])
    writing = progress.get("writing", [])

    reading_avg = None
    if reading:
        reading_avg = sum(r["score"] / r["total"] for r in reading) / len(reading) * 100

    writing_avg = None
    if writing:
        writing_avg = sum(w["band_estimate"] for w in writing) / len(writing)

    # Nothing done yet at all.
    if reading_avg is None and writing_avg is None:
        return {
            "greeting": "Welcome — let's find your starting point.",
            "suggestion": "Do one Reading passage and one Writing prompt so I can see where you're at.",
            "weak_area": None,
        }

    # Only one skill attempted so far — nudge toward the other.
    if reading_avg is not None and writing_avg is None:
        return {
            "greeting": f"Reading average: {reading_avg:.0f}%.",
            "suggestion": "You haven't tried Writing yet — do one prompt so I can compare your skills.",
            "weak_area": None,
        }
    if writing_avg is not None and reading_avg is None:
        return {
            "greeting": f"Writing average: band {writing_avg:.1f}.",
            "suggestion": "You haven't tried Reading yet — do one passage so I can compare your skills.",
            "weak_area": None,
        }

    # Both attempted — compare on a common 0-9-ish scale (reading % -> /9 scale).
    reading_as_band = reading_avg / 100 * 9
    if reading_as_band < writing_avg - 0.5:
        weak_area = "Reading"
        suggestion = "Reading looks like your weaker skill right now — do another passage and use Explain Bot on anything you get wrong."
    elif writing_avg < reading_as_band - 0.5:
        weak_area = "Writing"
        suggestion = "Writing looks like your weaker skill right now — try another prompt and read the AI feedback closely before rewriting."
    else:
        weak_area = None
        suggestion = "Reading and Writing are fairly balanced — keep alternating between them."

    return {
        "greeting": f"Reading ~{reading_avg:.0f}% | Writing band ~{writing_avg:.1f}",
        "suggestion": suggestion,
        "weak_area": weak_area,
    }


def _linear_trend(values):
    """Tiny linear-regression slope over (i, value). Returns slope per step."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den else 0.0


CRITERION_KEYS = [
    ("task_achievement_band", "Task Achievement", "TA"),
    ("coherence_cohesion_band", "Coherence & Cohesion", "CC"),
    ("lexical_resource_band", "Lexical Resource", "LR"),
    ("grammar_band", "Grammar", "GRA"),
]


def coach_detail(progress: dict) -> dict:
    """
    Deep view for the Coach page. Writing-first — reading coach comes later.

    Returns a dict the UI can render directly. Always present keys:
      - writing_count
      - writing_avg (None if no attempts)
      - writing_trend ("improving" / "flat" / "declining" / "insufficient data")
      - criterion_avgs {key: float or None}
      - weakest_criterion (key or None)
      - weakest_tip (string)
      - bands_history (list[float], for the line chart)
    """
    writing = progress.get("writing", [])

    if not writing:
        return {
            "writing_count": 0,
            "writing_avg": None,
            "writing_trend": "insufficient data",
            "criterion_avgs": {k: None for k, _, _ in CRITERION_KEYS},
            "weakest_criterion": None,
            "weakest_tip": "Submit a Writing task to unlock detailed coaching.",
            "bands_history": [],
        }

    bands = [w["band_estimate"] for w in writing if "band_estimate" in w]
    avg = sum(bands) / len(bands) if bands else None

    # Trend on the last 5 attempts (or all if fewer than 5).
    recent = bands[-5:] if len(bands) >= 5 else bands
    slope = _linear_trend(recent)
    if len(recent) < 2:
        trend = "insufficient data"
    elif slope > 0.15:
        trend = "improving"
    elif slope < -0.15:
        trend = "declining"
    else:
        trend = "flat"

    # Per-criterion averages (only over entries that recorded criterion bands).
    criterion_avgs = {}
    for key, _, _ in CRITERION_KEYS:
        vals = [w[key] for w in writing if key in w]
        criterion_avgs[key] = sum(vals) / len(vals) if vals else None

    # Pick the weakest criterion (lowest avg among criteria that have data).
    with_data = {k: v for k, v in criterion_avgs.items() if v is not None}
    weakest_key = min(with_data, key=with_data.get) if with_data else None

    TIPS = {
        "task_achievement_band":
            "Your Task Achievement has been the weakest — re-read the prompt before writing, "
            "and make sure every body paragraph directly answers it with a clear topic sentence.",
        "coherence_cohesion_band":
            "Coherence & Cohesion is your weak spot — use more linking phrases (however, "
            "in contrast, as a result) and start each paragraph with a topic sentence.",
        "lexical_resource_band":
            "Lexical Resource is lagging — replace common words with topic-specific vocabulary "
            "and try a few less-common collocations each essay.",
        "grammar_band":
            "Grammar is holding you back — vary your sentence structures (mix simple, compound, "
            "and complex) and double-check subject-verb agreement.",
    }
    weakest_tip = TIPS[weakest_key] if weakest_key else (
        "Keep submitting Writing tasks — once you have a few, I'll break down your "
        "criteria averages and tell you exactly what to fix."
    )

    return {
        "writing_count": len(writing),
        "writing_avg": avg,
        "writing_trend": trend,
        "criterion_avgs": criterion_avgs,
        "weakest_criterion": weakest_key,
        "weakest_tip": weakest_tip,
        "bands_history": bands,
    }

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="IELTS Practice", page_icon="📝", layout="centered")

# Forest + white theming. config.toml handles palette tokens; this block
# handles the bits config.toml can't reach (nav bar styling, button hover,
# metric tile rounding).
st.markdown(
    """
    <style>
      /* Horizontal radio as a top nav bar */
      div[data-testid="stRadio"] > div[role="radiogroup"] {
        gap: 0.25rem;
        background: #F5F8F4;
        padding: 0.35rem 0.6rem;
        border-radius: 12px;
        border: 1px solid #E2EBDF;
        justify-content: flex-start;
      }
      div[data-testid="stRadio"] label {
        padding: 0.35rem 0.9rem !important;
        border-radius: 8px;
        color: #1B2D20;
        font-weight: 500;
      }
      div[data-testid="stRadio"] label:has(input:checked) {
        background: #228B22;
        color: #FFFFFF !important;
      }
      div[data-testid="stRadio"] input { display: none; }

      /* Buttons */
      .stButton > button {
        border-radius: 10px;
        border: 1px solid #228B22;
        background: #FFFFFF;
        color: #228B22;
        font-weight: 600;
      }
      .stButton > button:hover {
        background: #228B22;
        color: #FFFFFF;
        border-color: #228B22;
      }
      div.stButton > button[kind="primary"],
      .stButton > button:focus {
        background: #228B22;
        color: #FFFFFF;
      }

      /* Metric tiles */
      div[data-testid="stMetric"] {
        background: #F5F8F4;
        border: 1px solid #E2EBDF;
        border-radius: 12px;
        padding: 0.6rem 0.8rem;
      }
      div[data-testid="stMetric"] label { color: #4A6A55; }

      /* Headings */
      h1 { color: #1B2D20; }
      h2, h3 { color: #1B2D20; }

      /* Hide the small "Press Enter to apply" hint under the radio */
      div[data-testid="stRadio"] + div small { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Top nav bar — replaces the old sidebar radio.
st.markdown("### 📝 IELTS Practice")
page = st.radio(
    "Navigate",
    ["🏠 Home", "🧭 Coach", "📖 Reading", "✍️ Writing", "🤖 Explain Bot", "📊 Progress"],
    horizontal=True,
    label_visibility="collapsed",
    key="nav",
)

# API key input row, directly under the nav.
api_col1, api_col2 = st.columns([3, 1])
with api_col1:
    sidebar_key = st.text_input(
        "Groq API key",
        type="password",
        value=st.session_state.get("groq_api_key", ""),
        help="Free key at https://console.groq.com/keys — auto-loaded from .env if present.",
        label_visibility="collapsed",
        placeholder="Groq API key (auto-loaded from .env)",
    )
    if sidebar_key and sidebar_key != st.session_state.get("groq_api_key"):
        st.session_state["groq_api_key"] = sidebar_key
with api_col2:
    st.caption(
        "🤖 Key: " + ("loaded ✅" if st.session_state.get("groq_api_key") else "not set")
    )

st.divider()

# ---------------- HOME ----------------
if page == "🏠 Home":
    st.title("📝 Welcome back")
    st.caption("Your personal IELTS practice companion — Reading, Writing, and an AI coach.")

    diagnosis = diagnose(st.session_state.progress)
    st.subheader(diagnosis["greeting"])
    st.info(f"👉 {diagnosis['suggestion']}")
    if diagnosis["weak_area"]:
        st.markdown(
            f"<span style='background:#228B22;color:#fff;padding:0.2rem 0.6rem;"
            f"border-radius:8px;font-weight:600;'>Focus: {diagnosis['weak_area']}</span>",
            unsafe_allow_html=True,
        )

    st.write("")
    c1, c2, c3 = st.columns(3)
    if c1.button("📖 Start Reading", use_container_width=True):
        st.session_state.nav = "📖 Reading"
        st.rerun()
    if c2.button("✍️ Start Writing", use_container_width=True):
        st.session_state.nav = "✍️ Writing"
        st.rerun()
    if c3.button("📊 View Progress", use_container_width=True):
        st.session_state.nav = "📊 Progress"
        st.rerun()

    if not st.session_state.get("groq_api_key"):
        st.warning(
            "No Groq API key detected. Drop your key into a `.env` file as "
            "`GROQ_API_KEY=...` and restart the app to unlock AI-graded Writing feedback."
        )

# ---------------- COACH ----------------
elif page == "🧭 Coach":
    st.title("🧭 Your Coach")
    detail = coach_detail(st.session_state.progress)

    if detail["writing_count"] == 0:
        st.info("Submit a Writing task to unlock detailed coaching.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Writing average", f"{detail['writing_avg']:.1f}" if detail["writing_avg"] else "—")
        trend_emoji = {
            "improving": "📈 Improving",
            "flat": "➡️ Flat",
            "declining": "📉 Declining",
            "insufficient data": "—",
        }[detail["writing_trend"]]
        m2.metric("Trend", trend_emoji)
        m3.metric("Attempts", detail["writing_count"])

        with_data = [(k, label, short) for k, label, short in CRITERION_KEYS
                     if detail["criterion_avgs"].get(k) is not None]
        if with_data:
            st.subheader("Criterion averages")
            cols = st.columns(len(with_data))
            for col, (k, label, _short) in zip(cols, with_data):
                col.metric(label, f"{detail['criterion_avgs'][k]:.1f}")

            if detail["weakest_criterion"]:
                wkey, wlabel, _ = next(
                    (k, label, s) for k, label, s in CRITERION_KEYS
                    if k == detail["weakest_criterion"]
                )
                st.error(f"**Weakest criterion: {wlabel}** — {detail['weakest_tip']}")
            else:
                st.success("All criteria are balanced — keep alternating between tasks.")
        else:
            st.caption(
                "Per-criterion averages will appear once your Writing tasks are AI-graded."
            )

        if detail["bands_history"]:
            st.subheader("Band trajectory")
            st.line_chart(detail["bands_history"])

    st.divider()
    st.caption(
        "Coach logic is Writing-first. The Reading coach will be added later — "
        "for now, Reading progress shows up on the Progress page."
    )

# ---------------- READING ----------------
elif page == "📖 Reading":
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
elif page == "✍️ Writing":
    st.title("✍️ Writing Practice")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        prompt = st.selectbox("Choose a prompt", WRITING_PROMPTS)
        st.write(f"**Prompt:** {prompt}")
        essay = st.text_area("Write your response here", height=420, key="essay_text")

        if st.button("Get Feedback"):
            if not essay.strip():
                st.warning("Write something first!")
            else:
                api_key = st.session_state.get("groq_api_key")
                result_payload = None

                if api_key:
                    with st.spinner("Grading against IELTS criteria..."):
                        ai_result = ai_writing_feedback(essay, prompt, api_key)

                    if "error" in ai_result:
                        st.warning(f"AI grading failed ({ai_result['error']}) — showing heuristic feedback instead.")
                        h = heuristic_writing_feedback(essay)
                        result_payload = {
                            "source": "heuristic",
                            "band_estimate": h["band_estimate"],
                            "criterion_bands": None,
                            "criteria_sentences": [
                                ("Word count", f"{h['word_count']} words ({h['sentence_count']} sentences)"),
                                ("Heuristic notes", " · ".join(h["notes"])),
                            ],
                            "overall_tip": "Heuristic is rough — set a Groq key for full IELTS-criteria feedback.",
                        }
                    else:
                        result_payload = {
                            "source": "ai",
                            "band_estimate": ai_result["band_estimate"],
                            "criterion_bands": {
                                "task_achievement_band": ai_result.get("task_achievement_band"),
                                "coherence_cohesion_band": ai_result.get("coherence_cohesion_band"),
                                "lexical_resource_band": ai_result.get("lexical_resource_band"),
                                "grammar_band": ai_result.get("grammar_band"),
                            },
                            "criteria_sentences": [
                                ("Task Achievement", ai_result.get("task_achievement", "")),
                                ("Coherence & Cohesion", ai_result.get("coherence_cohesion", "")),
                                ("Lexical Resource", ai_result.get("lexical_resource", "")),
                                ("Grammar", ai_result.get("grammar", "")),
                            ],
                            "overall_tip": ai_result.get("overall_tip", ""),
                        }
                else:
                    st.info("No API key set — showing rough heuristic feedback. Add a free Groq key for real AI grading.")
                    h = heuristic_writing_feedback(essay)
                    result_payload = {
                        "source": "heuristic",
                        "band_estimate": h["band_estimate"],
                        "criterion_bands": None,
                        "criteria_sentences": [
                            ("Word count", f"{h['word_count']} words ({h['sentence_count']} sentences)"),
                            ("Heuristic notes", " · ".join(h["notes"])),
                        ],
                        "overall_tip": "Heuristic is rough — set a Groq key for full IELTS-criteria feedback.",
                    }

                if result_payload:
                    st.session_state["writing_result"] = result_payload
                    # Persist into progress so the Coach can see it.
                    entry = {
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                        "band_estimate": result_payload["band_estimate"],
                        "source": result_payload["source"],
                    }
                    if result_payload["criterion_bands"]:
                        entry.update(result_payload["criterion_bands"])
                    st.session_state.progress["writing"].append(entry)
                    save_progress(st.session_state.progress)
                    st.rerun()

    with col_right:
        st.subheader("Feedback & coaching")
        result = st.session_state.get("writing_result")
        if not result:
            st.caption("👈 Write your essay on the left and click **Get Feedback** — your bands and AI commentary will appear here.")
        else:
            # Five band tiles in one row.
            band_cols = st.columns(5)
            band_cols[0].metric("Overall", f"{result['band_estimate']:.1f}")
            if result["criterion_bands"]:
                for i, (key, label, _short) in enumerate(CRITERION_KEYS, start=1):
                    band_cols[i].metric(label, f"{result['criterion_bands'][key]:.1f}")
            else:
                for i, (_, label, _short) in enumerate(CRITERION_KEYS, start=1):
                    band_cols[i].metric(label, "—")

            st.write("")
            for label, sentence in result["criteria_sentences"]:
                st.markdown(f"**{label}:** {sentence}")

            if result.get("overall_tip"):
                st.success(f"💡 {result['overall_tip']}")

# ---------------- EXPLAIN BOT ----------------
elif page == "🤖 Explain Bot":
    st.title("🤖 Explain Bot")
    st.write(
        "Paste a question you got wrong (or just want explained), your "
        "answer, and the correct answer. The bot will explain why in "
        "under 300 words."
    )

    api_key = st.session_state.get("groq_api_key")

    q_text = st.text_area("Question", height=100)
    col1, col2 = st.columns(2)
    with col1:
        user_ans = st.text_input("Your answer")
    with col2:
        correct_ans = st.text_input("Correct answer")

    if st.button("Explain"):
        if not api_key:
            st.warning("Add your Groq API key (auto-loaded from `.env` as `GROQ_API_KEY`) to use the bot.")
        elif not q_text.strip() or not correct_ans.strip():
            st.warning("Fill in at least the question and the correct answer.")
        else:
            with st.spinner("Thinking..."):
                explanation = ask_explainer_bot(q_text, user_ans, correct_ans, api_key)
            st.markdown(explanation)

# ---------------- PROGRESS ----------------
elif page == "📊 Progress":
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
            st.rerun()
