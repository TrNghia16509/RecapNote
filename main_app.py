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
from urllib.parse import urlencode
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import av
#from st_react_mic import st_react_mic
import streamlit.components.v1 as components
import base64
from audio_recorder_streamlit import audio_recorder

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
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://recapnote.up.railway.app")

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

# Bảng users
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY, 
    password TEXT, 
    email TEXT
)''')

# Bảng notes có json_url
c.execute('''CREATE TABLE IF NOT EXISTS notes (
    username TEXT, 
    title TEXT, 
    subject TEXT, 
    summary TEXT, 
    json_url TEXT, 
    timestamp TEXT
)''')

# Nếu DB cũ thiếu cột json_url thì thêm
try:
    c.execute("ALTER TABLE notes ADD COLUMN json_url TEXT")
except sqlite3.OperationalError:
    pass  # Cột đã tồn tại

conn.commit()

# ========= Tiêu đề và logo =========
st.set_page_config(page_title="RecapNote", layout="wide")
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://raw.githubusercontent.com/TrNghia16509/NoteBot/main/logo.png", width=150)
with col2:
    st.title("RecapNote - Ứng dụng AI ghi nhớ và tóm tắt văn bản")
    
# ================== Google OAuth Callback ==================
query_params = st.query_params
if "code" in query_params and not st.session_state.get("logged_in", False):
    code = query_params["code"]

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    token_res = requests.post(token_url, data=data)
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if access_token:
        user_info_res = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        profile = user_info_res.json()

        st.session_state.logged_in = True
        st.session_state.profile = profile
        st.session_state.username = profile.get("email", "google_user")

        # Nếu user chưa có trong DB thì thêm
        c.execute("SELECT * FROM users WHERE username=?", (st.session_state.username,))
        if not c.fetchone():
            c.execute("INSERT INTO users VALUES (?, ?, ?)",
                      (st.session_state.username, b"", profile.get("email")))
            conn.commit()

        st.success(f"✅ Đăng nhập Google thành công! Xin chào {st.session_state.username}")
        st.rerun()
    else:
        st.error("❌ Không lấy được access token từ Google.")
        
# ================== Login / Register ==================
def login():
    st.subheader("🔐 Đăng nhập")
    u = st.text_input("Tên đăng nhập hoặc email")
    p = st.text_input("Mật khẩu", type="password")
    if st.button("Đăng nhập", key="login_btn"):
        row = c.execute("SELECT * FROM users WHERE (username=? OR email=?)", (u, u)).fetchone()
        if row and bcrypt.checkpw(p.encode('utf-8'), row[1]):
            st.session_state.logged_in = True
            st.session_state.username = row[0]
            st.success("✅ Đăng nhập thành công!")
            st.rerun()
        else:
            st.error("Sai tài khoản hoặc mật khẩu.")

    # Đăng nhập với Google
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,  # URL gốc của app
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_link = f"{google_auth_url}?{urlencode(params)}"
    st.markdown(f"[🔐 Đăng nhập với Google]({auth_link})")

    # Quên mật khẩu
    if st.button("Quên mật khẩu?", key="forgot_btn"):
        email_reset = st.text_input("📧 Nhập email đã đăng ký")
        if email_reset:
            row = c.execute("SELECT username FROM users WHERE email=?", (email_reset,)).fetchone()
            if row:
                send_reset_email(email_reset, row[0])
            else:
                st.error("❌ Không tìm thấy email trong hệ thống.")

def register():
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

# ================== Sidebar ==================
with st.sidebar:
    st.markdown("## 🔑 Tài khoản")
    if st.session_state.get("logged_in", False):
        st.success(f"👋 Xin chào, **{st.session_state.username}**")
        if st.button("🚪 Đăng xuất", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.profile = None
            st.rerun()
    else:
        menu = st.radio("Chọn chức năng", ["Đăng nhập", "Đăng ký"])
        if menu == "Đăng nhập":
            login()
        else:
            register()
            
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
# Chọn ngôn ngữ
LANGUAGE_MAP = {
    "Auto Detect": "auto",
    "Vietnamese": "vi",
    "English": "en",
    "Japanese": "ja",
    "Korean": "ko",
    "French": "fr",
    "Chinese": "zh"
}

selected_lang_name = st.selectbox("Select language", list(LANGUAGE_MAP.keys()), index=1)
selected_lang_code = LANGUAGE_MAP[selected_lang_name]

# ========== Ghi âm (frontend) ==========
st.set_page_config(page_title="🎙 RecapNote Recorder", page_icon="🎙")

st.title("🎙 Ghi âm & gửi tới Flask Backend")

audio_bytes = audio_recorder(
    pause_threshold=2.0, 
    sample_rate=44100, 
    text="Nhấn để ghi âm"
)

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    if st.button("📤 Gửi tới Flask xử lý"):
        with st.spinner("Đang gửi file..."):
            files = {
                "file": ("recording.wav", audio_bytes, "audio/wav")
            }
            data = {
                "language_code": "vi"  # hoặc "auto"
            }
            try:
                res = requests.post(
                    "https://flask-recapnote.onrender.com/process_file",
                    files=files,
                    data=data,
                    timeout=120
                )
                if res.ok:
                    result = res.json()
                    st.success("✅ Kết quả từ backend")
                    st.write("**Chủ đề:**", result["subject"])
                    st.write("**Tóm tắt:**", result["summary"])
                    st.write("**File gốc:**", result["file_url"])
                    st.write("**JSON kết quả:**", result["json_url"])
                else:
                    st.error(f"Lỗi {res.status_code}: {res.text}")
            except Exception as e:
                st.error(f"Lỗi kết nối: {e}")

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

st.header("📤 Tải file để xử lý")
file = st.file_uploader("Chọn file (.mp3, .wav, .pdf, .docx)", type=["mp3", "wav", "pdf", "docx"])

if file:
    with st.spinner("⏳ Đang xử lý..."):
        # resp = requests.post(f"{API_URL}/process_file", files=files)
        # Khi gửi request
        res = requests.post(
            f"{API_URL}/process_file",
            files = {"file": (file.name, file, file.type)},
            data={"language_code": selected_lang_code},  # Gửi mã ngôn ngữ
            timeout=None,   # Không giới hạn thời gian chờ
            stream=True     # Hỗ trợ streaming kết quả
        )

    if res.status_code == 200:
        data = res.json()
        st.subheader("📌 Chủ đề")
        st.write(data["subject"])
        st.subheader("📚 Tóm tắt")
        st.write(data["summary"])
        st.subheader("📄 Nội dung")
        st.text_area("", data["full_text"], height=300, label_visibility="collapsed")

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
                    json_file_name = data["json_url"].split("/")[-2] + "/" + data["json_url"].split("/")[-1]
                    c.execute("INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?)", (
                        st.session_state.username,
                        data["subject"],
                        data["subject"],
                        data["summary"],
                        json_file_name,  # chỉ lưu tên file
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    st.success("Đã lưu!")
        else:
            st.info("🔒 Ghi chú tạm thời - hãy đăng nhập để lưu vĩnh viễn")
    else:
        st.error(f"Lỗi: {res.text}")

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
            if r[3]:
                if st.button("📥 Xem chi tiết", key=f"view_{r[0]}_{r[2]}"):
                    try:
                        # Gọi backend xin signed URL mới cho JSON
                        resp = requests.get(f"{API_URL}/get_note_json", params={"json_file": r[3]})
                        if resp.status_code == 200:
                            json_url = resp.json()["signed_url"]
                            json_data = requests.get(json_url).json()
                            st.text_area("📄 Nội dung", json_data.get("full_text", ""), height=300)
                            if json_data.get("file_url"):
                                st.markdown(f"[📂 Tải file gốc]({json_data['file_url']})")
                        else:
                            st.error("Không lấy được link JSON từ backend.")
                    except Exception as e:
                        st.error(f"❌ Lỗi tải file JSON: {e}")
            else:
                st.warning("⚠️ Ghi chú này chưa có file JSON.")
# ============ Chạy ==================
port = int(os.environ.get("PORT", 8501))

