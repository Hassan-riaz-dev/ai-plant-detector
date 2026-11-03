import json
import os

import streamlit as st
from groq import Groq

# ---------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------
st.set_page_config(page_title="AI Quiz Generator", page_icon="🧠", layout="centered")

st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
        padding: 28px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
    }
    .hero h1 { margin: 0; font-size: 2rem; color: white; }
    .hero p  { margin: 6px 0 0 0; opacity: 0.9; }
    .qcard {
        background: #f7f9f7;
        border: 1px solid #e0e6e0;
        border-radius: 12px;
        padding: 14px 18px 4px 18px;
        margin-bottom: 14px;
        color: #1b1b1b;
    }
    .score {
        font-size: 2.2rem;
        font-weight: 700;
        text-align: center;
        padding: 16px;
        border-radius: 14px;
        background: #e8f5e9;
        color: #1b5e20;
        margin: 10px 0 20px 0;
    }
    </style>
    <div class="hero">
        <h1>🧠 AI Quiz Generator</h1>
        <p>Type any topic or prompt and get an instant multiple-choice quiz.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

MODELS = {
    "Llama 3.3 70B (best quality)": "llama-3.3-70b-versatile",
    "Llama 3.1 8B (fastest)": "llama-3.1-8b-instant",
}

# ---------------------------------------------------------------
# API key handling
# ---------------------------------------------------------------
def get_api_key() -> str:
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass
    return os.getenv("GROQ_API_KEY", "")


# ---------------------------------------------------------------
# Quiz generation
# ---------------------------------------------------------------
def generate_quiz(api_key: str, model: str, prompt: str, n: int, difficulty: str):
    client = Groq(api_key=api_key)

    system_msg = (
        "You are an expert quiz creator. Respond ONLY with valid JSON in this exact format:\n"
        '{"questions": [{"question": "...", "options": ["A", "B", "C", "D"], '
        '"answer_index": 0, "explanation": "..."}]}\n'
        "Rules: exactly 4 options per question, answer_index is 0-3, "
        "only one correct answer, explanations are short and clear."
    )
    user_msg = (
        f"Create a {difficulty} difficulty multiple-choice quiz with {n} questions.\n"
        f"Topic / instructions: {prompt}"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    questions = []
    for q in data.get("questions", []):
        opts = q.get("options", [])
        idx = q.get("answer_index")
        if len(opts) == 4 and isinstance(idx, int) and 0 <= idx < 4:
            questions.append(q)
    if not questions:
        raise ValueError("The AI returned no valid questions. Please try again.")
    return questions


# ---------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = get_api_key()
    if not api_key:
        api_key = st.text_input("Groq API Key", type="password", help="Get one free at console.groq.com")
    else:
        st.success("API key loaded", icon="🔑")

    model_label = st.selectbox("Model", list(MODELS.keys()))
    num_q = st.slider("Number of questions", 3, 15, 5)
    difficulty = st.select_slider("Difficulty", ["Easy", "Medium", "Hard"], value="Medium")

# ---------------------------------------------------------------
# Session state
# ---------------------------------------------------------------
st.session_state.setdefault("questions", [])
st.session_state.setdefault("submitted", False)
st.session_state.setdefault("quiz_id", 0)

# ---------------------------------------------------------------
# Prompt input
# ---------------------------------------------------------------
prompt = st.text_area(
    "What should the quiz be about?",
    placeholder="e.g. Medicinal plants of Pakistan, or Python basics for beginners",
    height=100,
)

if st.button("✨ Generate Quiz", type="primary", use_container_width=True):
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar.")
    elif not prompt.strip():
        st.warning("Please enter a topic or prompt first.")
    else:
        with st.spinner("Creating your quiz..."):
            try:
                st.session_state.questions = generate_quiz(
                    api_key, MODELS[model_label], prompt.strip(), num_q, difficulty
                )
                st.session_state.submitted = False
                st.session_state.quiz_id += 1
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# ---------------------------------------------------------------
# Quiz display
# ---------------------------------------------------------------
questions = st.session_state.questions

if questions:
    st.divider()
    qid = st.session_state.quiz_id

    if not st.session_state.submitted:
        with st.form("quiz_form"):
            for i, q in enumerate(questions):
                st.markdown(f'<div class="qcard"><b>Q{i + 1}. {q["question"]}</b></div>', unsafe_allow_html=True)
                st.radio(
                    "Choose one:",
                    q["options"],
                    index=None,
                    key=f"q_{qid}_{i}",
                    label_visibility="collapsed",
                )
            if st.form_submit_button("✅ Submit Answers", use_container_width=True):
                st.session_state.submitted = True
                st.rerun()
    else:
        score = 0
        for i, q in enumerate(questions):
            chosen = st.session_state.get(f"q_{qid}_{i}")
            correct = q["options"][q["answer_index"]]
            is_right = chosen == correct
            score += is_right

            st.markdown(f'<div class="qcard"><b>Q{i + 1}. {q["question"]}</b></div>', unsafe_allow_html=True)
            if is_right:
                st.success(f"Your answer: {chosen} ✔")
            else:
                st.error(f"Your answer: {chosen if chosen else 'Not answered'}")
                st.info(f"Correct answer: {correct}")
            st.caption(f"💡 {q.get('explanation', '')}")

        st.markdown(
            f'<div class="score">Score: {score} / {len(questions)}</div>',
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Retake Quiz", use_container_width=True):
                st.session_state.submitted = False
                st.session_state.quiz_id += 1
                st.rerun()
        with col2:
            if st.button("🗑️ New Quiz", use_container_width=True):
                st.session_state.questions = []
                st.session_state.submitted = False
                st.rerun()

st.markdown("---")
st.caption("Built with Streamlit + Groq")
