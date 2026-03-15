import pytesseract
from PIL import Image
import streamlit as st
import ollama
from pypdf import PdfReader
from docx import Document

# -------------------- TESSERACT PATH --------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="AI Learning Assistant & Career Assistant",
    layout="wide"
)

st.title("🤖 AI Learning Assistant & Career Assistant")

# -------------------- SESSION INIT --------------------
def init():
    defaults = {
        "messages": [],
        "mode": "Q&A",
        "uploaded_content": "",
        "chat_history": [],
        "current_chat_id": 1,
        "share_text": "",
        "interview_active": False,
        "interview_index": 0,
        "interview_answers": [],
        "interview_questions": [],
        "generated_cover_letter": ""
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

# -------------------- FILE TEXT EXTRACTION --------------------
def extract_text_from_file(uploaded_file):

    text = ""

    if uploaded_file.type.startswith("image"):
        image = Image.open(uploaded_file)
        text = pytesseract.image_to_string(image)

    elif uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() or ""

    elif uploaded_file.name.endswith(".docx"):
        doc = Document(uploaded_file)
        for para in doc.paragraphs:
            text += para.text + "\n"

    else:
        text = uploaded_file.read().decode("utf-8")

    return text if text.strip() else "No readable text detected."

# -------------------- EXPORT --------------------
def export_chat(messages):
    return "\n\n".join([f"{m['role'].upper()}:\n{m['content']}" for m in messages])

def get_share_text(messages):
    return "\n\n".join([f"{m['role']}:\n{m['content']}" for m in messages])

# -------------------- SIDEBAR --------------------
st.sidebar.header("⚙️ Controls")

mode = st.sidebar.radio(
    "Select Mode",
    ["Q&A", "Interview", "AI Cover Letter Generator"]
)

st.session_state.mode = mode

# ---------- NEW CHAT ----------
if st.sidebar.button("➕ New Chat"):

    if st.session_state.messages:
        st.session_state.chat_history.append({
            "id": st.session_state.current_chat_id,
            "messages": st.session_state.messages.copy()
        })

        st.session_state.current_chat_id += 1

    st.session_state.messages = []
    st.session_state.uploaded_content = ""
    st.session_state.share_text = ""
    st.rerun()

# ---------- CLEAR CHAT ----------
if st.sidebar.button("🧹 Clear Current Chat"):
    st.session_state.messages = []
    st.rerun()

# ---------- EXPORT ----------
st.sidebar.download_button(
    "📤 Export Chat",
    export_chat(st.session_state.messages),
    file_name="chat_export.txt"
)

# ---------- SHARE ----------
if st.sidebar.button("🔗 Generate Share Text"):
    st.session_state.share_text = get_share_text(st.session_state.messages)

if st.session_state.share_text:
    st.sidebar.text_area("Copy & Share", st.session_state.share_text)

# ---------- CHAT HISTORY ----------
st.sidebar.subheader("🗂 Chat History")

for chat in st.session_state.chat_history:

    col1, col2 = st.sidebar.columns([3,1])

    if col1.button(f"💬 Chat {chat['id']}"):
        st.session_state.messages = chat["messages"]
        st.rerun()

    if col2.button("❌", key=f"delete_{chat['id']}"):
        st.session_state.chat_history = [
            c for c in st.session_state.chat_history
            if c["id"] != chat["id"]
        ]
        st.rerun()

# =========================================================
# ========================= Q&A MODE ======================
# =========================================================

if mode == "Q&A":

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    uploaded_files = st.file_uploader(
        "📎 Attach file(s)",
        type=["pdf", "txt", "docx", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    if uploaded_files:

        combined_text = ""

        for file in uploaded_files:
            combined_text += extract_text_from_file(file) + "\n\n"

        st.session_state.uploaded_content = combined_text

    user_input = st.chat_input("Ask something...")

    if user_input:

        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        context = st.session_state.uploaded_content

        if context:
            prompt = f"""
Document Content:
{context}

Question:
{user_input}
"""
            messages = [{"role": "user", "content": prompt}]

        else:
            messages = st.session_state.messages

        response = ollama.chat(
            model="llama3:8b",
            messages=messages
        )["message"]["content"]

        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )

        st.rerun()

# =========================================================
# ====================== INTERVIEW MODE ===================
# =========================================================
elif mode == "Interview":

    st.header("🎤 AI Interview Simulator")

    resume_file = st.file_uploader(
        "Upload Your Resume",
        type=["pdf","docx","txt","png","jpg","jpeg"]
    )

    role = st.text_input("Which role are you applying for?")

    resume_text = ""

    if resume_file:
        resume_text = extract_text_from_file(resume_file)

    # ---------- SESSION STATE ----------

    if "interview_active" not in st.session_state:
        st.session_state.interview_active = False

    if "interview_messages" not in st.session_state:
        st.session_state.interview_messages = []

    if "answer_key" not in st.session_state:
        st.session_state.answer_key = 0

    # ---------- START INTERVIEW ----------

    if not st.session_state.interview_active:

        if st.button("🚀 Start Interview"):

            if resume_text and role:

                system_prompt = f"""
You are a professional interviewer.

Candidate applied for role: {role}

Candidate Resume:
{resume_text}

Rules:

1 Ask ONE interview question at a time
2 Questions must be related to the role
3 Questions must use resume information
4 After answer evaluate it
5 Tell if answer is strong or weak
6 Provide correct or improved answer
7 Ask next question
"""

                st.session_state.interview_messages = [
                    {"role":"system","content":system_prompt}
                ]

                first_question = ollama.chat(
                    model="llama3:8b",
                    messages=st.session_state.interview_messages
                )["message"]["content"]

                st.session_state.interview_messages.append(
                    {"role":"assistant","content":first_question}
                )

                st.session_state.interview_active = True

                st.rerun()

            else:
                st.warning("Upload resume and enter role")

    # ---------- INTERVIEW RUNNING ----------

    else:

        # show AI messages
        for msg in st.session_state.interview_messages:

            if msg["role"] == "assistant":
                st.markdown(msg["content"])

        answer = st.text_area(
            "Your Answer",
            key=f"answer_box_{st.session_state.answer_key}"
        )

        col1,col2 = st.columns(2)

        # ---------- SUBMIT ANSWER ----------

        if col1.button("Submit Answer"):

            if answer.strip() == "":
                st.warning("Please type an answer")

            else:

                st.session_state.interview_messages.append(
                    {"role":"user","content":answer}
                )

                response = ollama.chat(
                    model="llama3:8b",
                    messages=st.session_state.interview_messages
                )["message"]["content"]

                st.session_state.interview_messages.append(
                    {"role":"assistant","content":response}
                )

                # change key -> clears textbox
                st.session_state.answer_key += 1

                st.rerun()

        # ---------- END INTERVIEW ----------

        if col2.button("End Interview"):

            transcript = "\n".join([
                m["content"] for m in st.session_state.interview_messages
            ])

            feedback_prompt = f"""
You are a senior hiring manager.

Based on this interview:

{transcript}

Give:

1 Strengths
2 Weaknesses
3 Suggestions
4 Final Score out of 10
"""

            feedback = ollama.chat(
                model="llama3:8b",
                messages=[{"role":"user","content":feedback_prompt}]
            )["message"]["content"]

            st.markdown("### 📊 Final Interview Feedback")
            st.markdown(feedback)

            st.session_state.interview_active = False
# =========================================================
# ================= COVER LETTER MODE =====================
# =========================================================

elif mode == "AI Cover Letter Generator":

    uploaded_files = st.file_uploader(
        "Upload Resume and/or Job Description",
        type=["pdf","docx","txt","png","jpg","jpeg"],
        accept_multiple_files=True
    )

    if uploaded_files and st.button("Generate Cover Letter"):

        texts = [extract_text_from_file(f) for f in uploaded_files]

        resume = texts[0]
        job = "\n\n".join(texts[1:]) if len(texts) > 1 else ""

        prompt = f"""
Generate a professional personalized cover letter.

Resume:
{resume}

Job Description:
{job}
"""

        cover_letter = ollama.chat(
            model="llama3:8b",
            messages=[{"role":"user","content":prompt}]
        )["message"]["content"]

        st.session_state.generated_cover_letter = cover_letter

    if st.session_state.generated_cover_letter:

        st.markdown("### Personalized Cover Letter")
        st.markdown(st.session_state.generated_cover_letter)

        st.download_button(
            "Download Cover Letter",
            st.session_state.generated_cover_letter,
            file_name="cover_letter.txt"
        )