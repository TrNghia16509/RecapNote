import streamlit as st
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from pydub import AudioSegment
import tempfile
import wave
import numpy as np
import queue
import threading
import google.generativeai as genai
import docx
from io import BytesIO
import secrets
import smtplib
from email.mime.text import MIMEText
import streamlit.web.bootstrap
from authlib.integrations.requests_client import OAuth2Session
import requests
from av import AudioFrame
import time
from b2sdk.v2 import InMemoryAccountInfo, B2Api
import bcrypt
from io import BytesIO
import json

# ========= Cấu hình =========
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RESET_URL = os.getenv("RESET_URL")
RESET_TOKEN_PATH = "reset_tokens"
os.makedirs(RESET_TOKEN_PATH, exist_ok=True)
info = InMemoryAccountInfo()
b2_api = B2Api(info)
b2_api.authorize_account("production", os.getenv("B2_APPLICATION_KEY_ID"), os.getenv("B2_APPLICATION_KEY"))
bucket = b2_api.get_bucket_by_name(os.getenv("B2_BUCKET_NAME"))

#================ Khởi tạo session_state ================
if "recording" not in st.session_state:
    st.session_state.recording = False
if "start_time" not in st.session_state:
    st.session_state.start_time = 0
if "audio_saved" not in st.session_state:
    st.session_state.audio_saved = False
if "audio_url" not in st.session_state:
    st.session_state.audio_url = ""
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "profile" not in st.session_state:
    st.session_state.profile = None
    
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
            row = c.execute("SELECT * FROM users WHERE (username=? OR email=?)", (u, u)).fetchone()
            if row and bcrypt.checkpw(p.encode('utf-8'), row[1]):
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
                hashed_pw = bcrypt.hashpw(pw1.encode('utf-8'), bcrypt.gensalt())
                c.execute("INSERT INTO users VALUES (?, ?, ?)", (new_user, hashed_pw, email))
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

# ========== Ghi âm (frontend) ==========
st.markdown("## 🎙 Ghi âm trực tiếp bằng trình duyệt")

# Giao diện HTML + JavaScript ghi âm
st.markdown("""
<style>
    button {
        margin-right: 10px;
    }
</style>

<button id="recordButton">🎙 Bắt đầu ghi âm</button>
<button id="stopButton" disabled>⏹ Dừng ghi</button>
<audio id="audioPlayback" controls></audio>
<script>
let mediaRecorder;
let audioChunks = [];
let startTime;

const recordButton = document.getElementById("recordButton");
const stopButton = document.getElementById("stopButton");
const audioPlayback = document.getElementById("audioPlayback");

recordButton.onclick = async function() {
    audioChunks = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        audioPlayback.src = audioUrl;

        const formData = new FormData();
        formData.append("file", audioBlob, "recorded.wav");

        const response = await fetch("https://flask-recapnote.onrender.com", {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        alert("📌 Chủ đề: " + result.subject + "\n📝 Tóm tắt: " + result.summary);
    };

    mediaRecorder.start();
    recordButton.disabled = true;
    stopButton.disabled = false;
    startTime = Date.now();
};

stopButton.onclick = function() {
    mediaRecorder.stop();
    recordButton.disabled = false;
    stopButton.disabled = true;
};
</script>
""", unsafe_allow_html=True)

# ==================== Tải file =====================
API_URL = os.getenv("FLASK_API_URL", "https://flask-recapnote.onrender.com")

# DB local để lưu metadata
conn = sqlite3.connect("notes.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS notes (
    username TEXT,
    title TEXT,
    subject TEXT,
    summary TEXT,
    json_url TEXT,
    timestamp TEXT)""")
conn.commit()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

st.header("📤 Tải file / ghi âm để xử lý")
file = st.file_uploader("Chọn file (.mp3, .wav, .pdf, .docx)", type=["mp3", "wav", "pdf", "docx"])

if file:
    with st.spinner("⏳ Đang xử lý..."):
        files = {"file": (file.name, file, file.type)}
        resp = requests.post(f"{API_URL}/process_file", files=files)
        if resp.status_code == 200:
            data = resp.json()
            st.subheader("📌 Chủ đề")
            st.write(data["subject"])
            st.subheader("📚 Tóm tắt")
            st.write(data["summary"])
            st.subheader("📄 Nội dung")
            st.text_area("Full Text", data["full_text"], height=300, label_visibility="collapsed")

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
                
            if st.session_state.logged_in:
                if st.button("💾 Lưu ghi chú"):
                    c.execute("INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?)", (
                        st.session_state.username,
                        data["subject"],
                        data["subject"],
                        data["summary"],
                        data["json_url"],
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    st.success("Đã lưu!")
        else:
            st.info("🔒 Ghi chú tạm thời - hãy đăng nhập để lưu vĩnh viễn")

# ========= Hiển thị ghi chú =========
if st.session_state.logged_in:
    st.subheader("📂 Ghi chú đã lưu")
    rows = c.execute(
        "SELECT title, summary, timestamp, json_url FROM notes WHERE username=?",
        (st.session_state.username,)
    ).fetchall()
    for r in rows:
        with st.expander(f"📝 {r[0]} ({r[2][:10]})"):
            st.markdown(f"**Tóm tắt:** {r[1]}")
            if st.button("📥 Xem chi tiết", key=r[3]):
                json_data = requests.get(r[3]).json()
                st.text_area("📄 Nội dung", json_data["full_text"], height=300)
                st.markdown(f"[Tải file gốc]({json_data['file_url']})")
# ============ Chạy ==================
port = int(os.environ.get("PORT", 8501))

