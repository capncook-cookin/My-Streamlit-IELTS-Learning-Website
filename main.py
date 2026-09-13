"""
IELTS Practice API — FastAPI backend

Run locally with:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Converted from a Streamlit prototype — every grading/coaching function below
is unchanged from that version, just exposed over HTTP instead of rendered
directly by Streamlit. The Next.js frontend calls these endpoints.
"""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
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
# Groq's llama-3.3-70b-versatile was decommissioned late 2025;
# gpt-oss-20b is the current fast/cheap open model on Groq's free tier.
GROQ_MODEL = "openai/gpt-oss-20b"

# The chat widget has no key-input field in the UI, so its key comes from
# the backend's own .env instead — set GROQ_API_KEY there.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Ollama runs locally — used for the Writing coach because it's free and
# gives us more control over the grading model. Override via .env if needed.
# llama3.2:3b is roughly 2x faster than llama3.1:8b on CPU (~60s vs ~195s
# for a typical essay) with comparable grading quality on rubric-anchored
# prompts. Pull with: ollama pull llama3.2:3b
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

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

def groq_chat(messages, api_key):
    """
    Sends the full conversation history to Groq and returns the assistant's
    reply. `messages` is a list of {"role", "content"} dicts.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.7,
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
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

# In-memory progress, seeded from disk on startup — same data load_progress()
# was already doing, just without Streamlit's session_state wrapper.
_progress = load_progress()

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

    # Official IELTS rule: responses of 20 words or fewer are capped at Band 1,
    # no matter what. Without this check the scorer below just defaults to a
    # 5.0 baseline for empty/near-empty text, which is clearly wrong.
    if word_count <= 20:
        note = f"Only {word_count} word(s) written — IELTS caps responses of 20 words or fewer at Band 1."
        return {
            "band_estimate": 1.0,
            "task_achievement_band": 1.0,
            "coherence_cohesion_band": 1.0,
            "lexical_resource_band": 1.0,
            "grammar_band": 1.0,
            "task_achievement": note,
            "coherence_cohesion": note,
            "lexical_resource": note,
            "grammar": note,
            "overall_tip": "Write a full response — aim for 250+ words on Task 2.",
            "source": "heuristic",
        }

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
    band_estimate = round(min(band_estimate, 8.0), 1)

    # Same shape as ai_writing_feedback()'s return value, so the frontend
    # doesn't need to branch depending on which path graded the essay.
    return {
        "band_estimate": band_estimate,
        "task_achievement_band": band_estimate,
        "coherence_cohesion_band": band_estimate,
        "lexical_resource_band": band_estimate,
        "grammar_band": band_estimate,
        "task_achievement": notes[0],
        "coherence_cohesion": notes[1],
        "lexical_resource": notes[2],
        "grammar": "Grammar can't be checked without AI grading — this is a rough placeholder.",
        "overall_tip": "This is a rough placeholder score, not real AI grading.",
        "source": "heuristic",
    }

# ---------------------------------------------------------------------------
# REAL AI WRITING GRADING — replaces the heuristic placeholder when an API
# key is available. Grades against the four official IELTS writing criteria.
# ---------------------------------------------------------------------------
def ai_writing_feedback(essay: str, prompt: str, api_key: str) -> dict:
    # Rubric below is a one-line-per-band compression of the official
    # public IELTS Task 2 band descriptors (British Council / IDP /
    # Cambridge). The original full rubric is ~1,200 tokens of system
    # prompt — the 3B model can use a shorter anchor without losing
    # grading quality, and prompt-eval drops from ~24s to ~4s.
    # Full rubric source: https://takeielts.britishcouncil.org/sites/default/files/ielts_writing_band_descriptors.pdf
    band_rubric = (
        "TASK RESPONSE: 9 fully explores prompt, developed position, strong support. "
        "8 mostly developed with minor gaps. 7 addresses main parts, some over-generalization. "
        "6 uneven, unclear/repetitive conclusions, underdeveloped ideas. "
        "5 partial, inconsistent development. 4 barely engages, unclear ideas. 1-3 minimal.\n\n"
        "COHERENCE & COHESION: 9 effortless flow, invisible cohesion. "
        "8 logical with minor lapses. 7 clear progression, minor cohesive-device issues. "
        "6 generally coherent, mechanical linking. 5 inconsistent progression. "
        "4 no clear progression. 1-3 no organization.\n\n"
        "LEXICAL RESOURCE: 9 wide/precise/natural, vanishingly rare errors. "
        "8 wide, skillful, occasional slips. 7 sufficient range, some imprecise word choice. "
        "6 adequate but restricted. 5 limited, frequent lapses. "
        "4 basic/repetitive/ill-suited. 1-3 extremely limited.\n\n"
        "GRAMMATICAL RANGE & ACCURACY: 9 wide range, near-flawless control. "
        "8 wide/accurate, most error-free. 7 good complex variety with occasional slips. "
        "6 mix of simple/complex, errors rarely block meaning. 5 limited/repetitive, frequent errors. "
        "4 narrow range, frequent errors. 1-3 little control."
    )

    system_prompt = (
        "You are an official IELTS Writing examiner grading a Task 2 essay. "
        "Use the rubric below to anchor every band you assign.\n\n"
        f"{band_rubric}\n\n"
        "For EACH of the four categories, write a 3-4 sentence breakdown: "
        "quote or reference something SPECIFIC the writer did well, something SPECIFIC "
        "that held the band back, and what changing it would look like. Be concise.\n\n"
        "Respond ONLY in raw JSON, no markdown fences, no preamble, in this exact shape: "
        '{"band_estimate": <number 1-9 one decimal>, '
        '"task_achievement_band": <number 1-9 one decimal>, '
        '"coherence_cohesion_band": <number 1-9 one decimal>, '
        '"lexical_resource_band": <number 1-9 one decimal>, '
        '"grammar_band": <number 1-9 one decimal>, '
        '"task_achievement": "<3-4 sentences: strengths, weaknesses, what to change>", '
        '"coherence_cohesion": "<3-4 sentences: strengths, weaknesses, what to change>", '
        '"lexical_resource": "<3-4 sentences: strengths, weaknesses, what to change>", '
        '"grammar": "<3-4 sentences: strengths, weaknesses, what to change>", '
        '"overall_tip": "<one sentence, single most useful thing to fix next>"}'
    )
    user_prompt = f"Prompt: {prompt}\n\nEssay:\n{essay}"

    # Ollama's /api/chat takes the same OpenAI-shaped messages list, plus a
    # `format: "json"` flag that nudges the model to emit valid JSON.
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        # num_predict 800 — enough for 4 x ~3-sentence breakdowns + JSON
        # overhead, well under Ollama's default 128 token cap but with real
        # headroom. With the 3B model on CPU this finishes in ~60s.
        # num_ctx 4096 — limits KV cache to keep prompt-eval cheap.
        "options": {"temperature": 0.3, "num_predict": 800, "num_ctx": 4096},
    }
    try:
        response = requests.post(
            # 180s — the 3B model on CPU finishes a typical grade in ~60s;
            # 180s leaves headroom for cold-loads and longer essays without
            # hanging the frontend indefinitely.
            f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=180
        )
        response.raise_for_status()
        raw = response.json()["message"]["content"]
        # Model sometimes wraps JSON in code fences despite instructions — strip them.
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(raw)
        parsed["source"] = "ai"
        return parsed
    except requests.exceptions.Timeout:
        print("[ai_writing_feedback] Ollama request timed out after 180s.")
        return {"error": "⚠️ Ollama took too long to respond (>180s) — falling back to heuristic scoring."}
    except requests.exceptions.ConnectionError:
        print(f"[ai_writing_feedback] Can't connect to Ollama at {OLLAMA_BASE_URL}.")
        return {"error": (
            f"⚠️ Can't reach Ollama at {OLLAMA_BASE_URL}. Is it running? "
            "Try: ollama serve"
        )}
    except requests.exceptions.HTTPError:
        print(f"[ai_writing_feedback] Ollama HTTP error: {response.status_code} — {response.text[:300]}")
        if response.status_code == 404:
            return {"error": (
                f"⚠️ Ollama can't find model '{OLLAMA_MODEL}'. "
                f"Run: ollama pull {OLLAMA_MODEL}"
            )}
        return {"error": f"⚠️ Ollama API error: HTTP {response.status_code}"}
    except json.JSONDecodeError as e:
        print(f"[ai_writing_feedback] Model didn't return valid JSON: {e}\nRaw content: {raw[:500]}")
        return {"error": f"⚠️ Model response wasn't valid JSON: {e}"}
    except (requests.exceptions.RequestException, KeyError) as e:
        print(f"[ai_writing_feedback] Unexpected error: {e}")
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
# API — wraps the functions above, none of their logic changed.
# ---------------------------------------------------------------------------
app = FastAPI(title="IELTS Practice API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GradeRequest(BaseModel):
    prompt: str
    essay: str
    api_key: str | None = None  # optional Groq key; falls back to .env / heuristic


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


CHAT_SYSTEM_PROMPT = (
    "You are the CtrlLang guide, a friendly, concise IELTS study assistant "
    "embedded in a practice app. Help with study strategy, IELTS format "
    "questions, and quick encouragement. Keep replies short — a few "
    "sentences, not an essay — since this is a small chat widget, not a "
    "full page."
)


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="No GROQ_API_KEY set in the backend's .env file.",
        )
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message is empty.")

    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    reply = groq_chat(messages, GROQ_API_KEY)
    return {"reply": reply}


@app.get("/api/prompts")
def get_prompts():
    return WRITING_PROMPTS


@app.get("/api/word-count")
def word_count(essay: str):
    """
    Pre-submit word-count check.

    Frontend calls this BEFORE the user clicks Submit on the writing page
    so it can show a warning and disable the button when the essay is
    shorter than the minimum. Returns the same numbers /api/grade uses
    (same regex), so the UI and the backstop can't disagree.
    """
    # Same regex the heuristic grader uses — keep these in sync if you
    # ever change one.
    count = len(re.findall(r"\b\w+\b", essay or ""))
    min_words = 150
    ok = count >= min_words
    if count == 0:
        message = "Write your essay first — the word count is 0."
    elif ok:
        message = f"Word count OK ({count} words)."
    else:
        message = (
            f"Essay is {count} words — IELTS requires at least {min_words}. "
            "Please write more before submitting."
        )
    return {"count": count, "min_words": min_words, "ok": ok, "message": message}


@app.post("/api/grade")
def grade_essay(req: GradeRequest):
    if not req.essay.strip():
        raise HTTPException(status_code=400, detail="Essay is empty.")

    # Hard backstop: even if the UI somehow lets a too-short essay through
    # (devtools, curl, an older frontend build, etc.), reject it here so
    # short essays never reach the grader. Use JSONResponse instead of
    # HTTPException so the frontend gets structured word_count + min_words
    # fields (HTTPException would only serialize `detail`).
    essay_word_count = len(re.findall(r"\b\w+\b", req.essay))
    MIN_ESSAY_WORDS = 150
    if essay_word_count < MIN_ESSAY_WORDS:
        return JSONResponse(
            status_code=400,
            content={
                "detail": (
                    f"Essay is {essay_word_count} words — IELTS requires at "
                    f"least {MIN_ESSAY_WORDS}. Write more before submitting."
                ),
                "word_count": essay_word_count,
                "min_words": MIN_ESSAY_WORDS,
                "ok": False,
            },
        )

    result = ai_writing_feedback(req.essay, req.prompt, req.api_key)
    if "error" in result:
        result = heuristic_writing_feedback(req.essay)

    _progress["writing"].append({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "band_estimate": result["band_estimate"],
        "source": result.get("source", "heuristic"),
    })
    save_progress(_progress)

    return result


# ---------------------------------------------------------------------------
# Mount the Groq-powered vocabulary helper. Lives in its own module so the
# rest of main.py (heuristics, AI grader, chat) stays untouched.
# ---------------------------------------------------------------------------
from vocab_routes import router as vocab_router
app.include_router(vocab_router)
