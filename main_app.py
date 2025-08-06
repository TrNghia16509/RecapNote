import streamlit as st
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from pydub import AudioSegment
import tempfile
import wave
import numpy as np
import queue
import threading
import google.generativeai as genai
import fitz  # PyMuPDF
import docx
from io import BytesIO
import secrets
import smtplib
from email.mime.text import MIMEText
import streamlit.web.bootstrap
from authlib.integrations.requests_client import OAuth2Session
import requests
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import av
import time

# ========= Cấu hình =========
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RESET_URL = os.getenv("RESET_URL")
RESET_TOKEN_PATH = "reset_tokens"
os.makedirs(RESET_TOKEN_PATH, exist_ok=True)
#================ Khởi tạo session_state ================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "profile" not in st.session_state:
    st.session_state.profile = None

# Khởi tạo session state
if "recording" not in st.session_state:
    st.session_state.recording = False

if "audio_buffer" not in st.session_state:
    st.session_state.audio_buffer = []

if "recorded_file_path" not in st.session_state:
    st.session_state.recorded_file_path = None

if "start_time" not in st.session_state:
    st.session_state.start_time = 0

if "temp_wav_file" not in st.session_state:
    st.session_state.temp_wav_file = None
    
if "summary_result" not in st.session_state:
    st.session_state.summary_result = None

if "audio_frames" not in st.session_state:
    st.session_state.audio_frames = []
    
#==================== Đặt lại mật khẩu ============================
query_params = st.query_params
token = query_params.get("reset_token", [None])[0]
if token:
    try:
        with open(f"{RESET_TOKEN_PATH}/{token}.txt", "r") as f:
            username_token = f.read().strip()
    except:
        st.error("❌ Mã xác thực không hợp lệ hoặc đã hết hạn.")
        st.stop()

    st.title("🔒 Đặt lại mật khẩu mới")
    new_pass = st.text_input("🔑 Mật khẩu mới", type="password")
    confirm = st.text_input("🔁 Xác nhận mật khẩu", type="password")
    if st.button("Cập nhật mật khẩu"):
        if new_pass != confirm:
            st.warning("⚠️ Mật khẩu không khớp.")
        else:
            c.execute("UPDATE users SET password=? WHERE username=?", (new_pass, username_token))
            conn.commit()
            os.remove(f"{RESET_TOKEN_PATH}/{token}.txt")
            st.success("✅ Mật khẩu đã được cập nhật.")
            st.stop()

#================= Gửi reset email ====================
def send_reset_email(email, username):
    reset_token = secrets.token_urlsafe(24)
    reset_link = f"{RESET_URL}/?reset_token={reset_token}"
    with open(f"{RESET_TOKEN_PATH}/{reset_token}.txt", "w") as f:
        f.write(username)

    msg = MIMEText(f"""Xin chào {username},

Bạn vừa yêu cầu đặt lại mật khẩu cho tài khoản RecapNote.

👉 Nhấn vào đường dẫn sau để đổi mật khẩu:
{reset_link}

Nếu bạn không yêu cầu, vui lòng bỏ qua email này.

Trân trọng,
RecapNote""")

    msg["Subject"] = "🔐 Khôi phục mật khẩu RecapNote"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        st.success("✅ Đã gửi email khôi phục. Kiểm tra hộp thư!")
    except Exception as e:
        st.error(f"❌ Gửi mail thất bại: {e}")

# ========= Cơ sở dữ liệu =========
conn = sqlite3.connect("notes.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY, password TEXT, email TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notes (
    username TEXT, title TEXT, subject TEXT, summary TEXT, content TEXT, timestamp TEXT, note TEXT)''')
conn.commit()

# ========= Tiêu đề và logo =========
st.set_page_config(page_title="RecapNote", layout="wide")
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://raw.githubusercontent.com/TrNghia16509/NoteBot/main/logo.png", width=150)
with col2:
    st.title("RecapNote - Ứng dụng AI ghi nhớ và tóm tắt văn bản")

# ========= Sidebar: Đăng nhập / Đăng ký ========= 
def login():
    with st.sidebar:
        st.subheader("🔐 Đăng nhập")
        u = st.text_input("Tên đăng nhập hoặc email")
        p = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập", key="login_btn"):
            row = c.execute("SELECT * FROM users WHERE (username=? OR email=?) AND password=?", (u, u, p)).fetchone()
            if row:
                st.session_state.logged_in = True
                st.session_state.username = row[0]
                st.success("✅ Đăng nhập thành công!")
            else:
                st.error("Sai tài khoản hoặc mật khẩu.")

        # Đăng nhập bằng Google
        if st.button("🔐 Đăng nhập với Google", key="google_login_btn"):
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            redirect_uri = "https://recapnote.up.railway.app/"

            oauth = OAuth2Session(
                client_id,
                client_secret,
                scope="openid email profile",
                redirect_uri=redirect_uri
            )
            uri, state = oauth.create_authorization_url("https://accounts.google.com/o/oauth2/auth")
            st.markdown(f"[Nhấn vào đây để đăng nhập bằng Google]({uri})")

        if st.button("Quên mật khẩu?", key="forgot_btn"):
            email_reset = st.text_input("📧 Nhập email đã đăng ký")
            if email_reset:
                row = c.execute("SELECT username FROM users WHERE email=?", (email_reset,)).fetchone()
                if row:
                    send_reset_email(email_reset, row[0])
                else:
                    st.error("❌ Không tìm thấy email trong hệ thống.")

def register():
    with st.sidebar:
        st.subheader("🆕 Đăng ký")
        new_user = st.text_input("Tên đăng nhập mới")
        email = st.text_input("Email")
        pw1 = st.text_input("Mật khẩu", type="password")
        pw2 = st.text_input("Xác nhận mật khẩu", type="password")
        if st.button("Đăng ký", key="register_btn"):
            if pw1 != pw2:
                st.warning("❌ Mật khẩu không khớp.")
            else:
                c.execute("INSERT INTO users VALUES (?, ?, ?)", (new_user, pw1, email))
                conn.commit()
                st.success("✅ Đăng ký thành công. Hãy đăng nhập.")

with st.sidebar:
    st.markdown("## 🔑 Tài khoản")
    menu = st.radio("Chọn chức năng", ["Đăng nhập", "Đăng ký"])
    if menu == "Đăng nhập":
        login()
    else:
        register()

    if st.session_state.logged_in or st.session_state.profile:
        if st.button("🚪 Đăng xuất", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.profile = None
            st.success("✅ Đã đăng xuất.")

# ========= Hướng dẫn sử dụng =========
with st.expander("📘 Hướng dẫn sử dụng"):
    st.markdown("""
**1. Tải file hoặc ghi âm trực tiếp**
- Hỗ trợ định dạng: .mp3, .wav, .pdf, .docx

**2. Chọn ngôn ngữ**
- Gợi ý đúng ngôn ngữ của bài giảng để chuyển văn bản chính xác hơn

**3. Tóm tắt, lưu và hỏi đáp**
- Có thể hỏi thêm về nội dung thông qua Chatbox thông minh

**4. Ghi chú**
- Nếu chưa đăng nhập, ghi chú sẽ tạm thời và xóa khi đóng web
- Nếu đã đăng nhập, có thể lưu ghi chú vào hệ thống
""")

# ========= Chọn ngôn ngữ =========
lang = st.selectbox("🌍 Chọn ngôn ngữ đầu vào", ["auto", "vi", "en", "fr", "ja"])

#=========== Ghi âm (frontend) ===========
st.markdown("## 🎙 Ghi âm trực tiếp bằng trình duyệt")

def audio_frame_callback(frame):
    audio = np.frombuffer(frame.to_ndarray(), dtype=np.int16)
    st.session_state.audio_frames.append(audio)

col1, col2 = st.columns([1, 3])
with col1:
    btn_label = "⏹ Dừng ghi âm" if st.session_state.recording else "🎙 Bắt đầu ghi âm"
    if st.button(btn_label):
        if not st.session_state.recording:
            st.session_state.audio_frames = []
            st.session_state.recording = True
            st.session_state.start_time = time.time()
        else:
            st.session_state.recording = False
            if st.session_state.audio_frames:
                raw_audio = np.concatenate(st.session_state.audio_frames)
                reduced_audio = nr.reduce_noise(
                    y=raw_audio.astype(np.float32),
                    sr=16000,
                    prop_decrease=1.0
                )
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                sf.write(temp_file.name, reduced_audio, 16000)
                st.session_state.temp_wav_file = temp_file.name
                st.success("🎧 Đã lưu bản ghi!")

with col2:
    if st.session_state.recording:
        elapsed = int(time.time() - st.session_state.start_time)
        m, s = divmod(elapsed, 60)
        st.success(f"🔴 Đang ghi âm... {m:02}:{s:02}")

if st.session_state.recording:
    webrtc_streamer(
        key="recorder",
        mode=WebRtcMode.SENDONLY,
        audio_frame_callback=audio_frame_callback,
        media_stream_constraints={"audio": True, "video": False},
    )

if st.session_state.temp_wav_file and os.path.exists(st.session_state.temp_wav_file):
    st.markdown("### 🔁 Nghe lại bản ghi")
    st.audio(open(st.session_state.temp_wav_file, "rb").read(), format="audio/wav")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📤 Gửi lên Flask"):
            with open(st.session_state.temp_wav_file, "rb") as f:
                files = {"file": f}
                try:
                    res = requests.post("https://flask-recapnote.onrender.com/upload_audio", files=files)
                    if res.ok:
                        data = res.json()
                        st.success("✅ Gửi thành công!")
                        st.markdown(f"**📌 Chủ đề:** {data['subject']}")
                        st.markdown(f"**📝 Tóm tắt:** {data['summary']}")

                        with open(st.session_state.temp_wav_file, "rb") as download_file:
                            st.download_button(
                                label="⬇️ Tải bản ghi",
                                data=download_file.read(),
                                file_name="recorded_clean.wav",
                                mime="audio/wav",
                            )

                        os.remove(st.session_state.temp_wav_file)
                        st.session_state.temp_wav_file = None
                except Exception as e:
                    st.error(f"❌ Gửi thất bại: {e}")

    with col_b:
        if st.button("🔁 Ghi lại"):
            os.remove(st.session_state.temp_wav_file)
            st.session_state.temp_wav_file = None
            st.experimental_rerun()
                
# ========= Tải file hoặc ghi âm =========
uploaded_file = st.file_uploader("📤 Tải lên file (.mp3, .wav, .pdf, .docx)", type=["mp3", "wav", "pdf", "docx"])

def transcribe_audio(file, language="vi"):
    model = WhisperModel("small", compute_type="int8")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(file.read())
        tmp_path = tmp.name
    segments, info = model.transcribe(tmp_path, language=None if language == "auto" else language)
    os.remove(tmp_path)
    return "\n".join([seg.text for seg in segments]), info.language

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

# ========= Phân loại và xử lý =========
text_result = ""
if uploaded_file:
    if uploaded_file.name.endswith(".pdf"):
        text_result = extract_text_from_pdf(uploaded_file)
    elif uploaded_file.name.endswith(".docx"):
        text_result = extract_text_from_docx(uploaded_file)
    else:
        text_result, lang_detected = transcribe_audio(uploaded_file, language=lang)
    st.success("✅ Nội dung đã xử lý:")
    st.text_area("📄 Nội dung", text_result, height=300)

    # Tóm tắt và AI xử lý
    model = genai.GenerativeModel("gemini-1.5-flash")
    subject_prompt = f"Chủ đề chính của nội dung sau là gì? {text_result}"
    
    subject = model.generate_content(subject_prompt).text.strip()

    summary_prompt = f"Bạn là chuyên gia về {subject}. Tóm tắt nội dung: {text_result}"
    summary = model.generate_content(summary_prompt).text.strip()

    st.subheader("📚 Tóm tắt bởi AI")
    st.write(summary)

    # Chatbot
    st.markdown("### 🤖 Hỏi gì thêm về nội dung?")
    if "chat" not in st.session_state:
        st.session_state.chat = []
    for msg in st.session_state.chat:
        st.chat_message(msg["role"]).write(msg["content"])
    q = st.chat_input("Nhập câu hỏi...")
    if q:
        st.chat_message("user").write(q)
        ai = model.start_chat(history=[{"role": "user", "parts": text_result}])
        r = ai.send_message(q)
        st.chat_message("assistant").write(r.text)
        st.session_state.chat.append({"role": "user", "content": q})
        st.session_state.chat.append({"role": "assistant", "content": r.text})

    # Ghi chú và lưu
    title = subject
    note = st.text_input("📝 Ghi chú thêm")
    if st.session_state.logged_in:
        if st.button("💾 Lưu ghi chú"):
            c.execute("INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?, ?)", (
                st.session_state.username, title, subject, summary, text_result,
                datetime.now().isoformat(), note
            ))
            conn.commit()
            st.success("Đã lưu!")
    else:
        st.info("🔒 Ghi chú tạm thời - hãy đăng nhập để lưu vĩnh viễn")

# ========= Hiển thị ghi chú =========
if st.session_state.logged_in:
    st.subheader("📂 Ghi chú đã lưu")
    rows = c.execute("SELECT title, summary, timestamp, note FROM notes WHERE username=?", (st.session_state.username,)).fetchall()
    for r in rows:
        with st.expander(f"📝 {r[0]} ({r[2][:10]})"):

            st.markdown(f"**Tóm tắt:** {r[1]}")
            st.markdown(f"**Ghi chú:** {r[3]}")
# ============ Chạy ==================
port = int(os.environ.get("PORT", 8501))

