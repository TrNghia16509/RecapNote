import streamlit as st
import sqlite3
from datetime import datetime
from faster_whisper import WhisperModel
import tempfile
import os
import google.generativeai as genai
from dotenv import load_dotenv
from pydub import AudioSegment
from streamlit_webrtc import webrtc_streamer#, WebRtcMode, ClientSettings
import av
import numpy as np
import queue

# Load môi trường cho Gemini
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Định nghĩa cấu trúc tóm tắt cho từng môn học
SUBJECT_TEMPLATES = {
    "Toán học": """
    1. KHÁI NIỆM & ĐỊNH LÝ:
    - Các định nghĩa và khái niệm mới
    - Các định lý và công thức quan trọng
    - Điều kiện áp dụng

    2. PHƯƠNG PHÁP & KỸ THUẬT:
    - Các phương pháp giải chính
    - Kỹ thuật tính toán
    - Các bước giải quan trọng

    3. VÍ DỤ & BÀI TẬP MẪU:
    - Phân tích các ví dụ tiêu biểu
    - Các dạng bài tập điển hình

    4. GHI CHÚ HỌC TẬP:
    - Các lỗi thường gặp cần tránh
    - Mẹo và thủ thuật giải nhanh
    - Liên hệ với các chủ đề khác
    """,
    
    "Vật lý": """
    1. NGUYÊN LÝ & ĐỊNH LUẬT:
    - Các định luật vật lý mới
    - Nguyên lý hoạt động
    - Các công thức quan trọng

    2. HIỆN TƯỢNG & ỨNG DỤNG:
    - Giải thích hiện tượng
    - Ứng dụng thực tế
    - Thí nghiệm liên quan

    3. PHÂN TÍCH ĐỊNH LƯỢNG:
    - Các đại lượng và đơn vị
    - Quan hệ giữa các đại lượng
    - Phương pháp giải bài tập

    4. GHI CHÚ HỌC TẬP:
    - Các điểm cần lưu ý
    - Liên hệ với các chương khác
    - Câu hỏi ôn tập quan trọng
    """,
    
    "Hóa học": """
    1. KHÁI NIỆM & PHẢN ỨNG:
    - Định nghĩa và khái niệm mới
    - Các phản ứng hóa học chính
    - Điều kiện phản ứng

    2. CƠ CHẾ & QUY LUẬT:
    - Cơ chế phản ứng
    - Các quy luật quan trọng
    - Yếu tố ảnh hưởng

    3. THỰC HÀNH & ỨNG DỤNG:
    - Phương pháp thí nghiệm
    - Ứng dụng trong thực tế
    - Các bài toán thực tế

    4. GHI CHÚ HỌC TẬP:
    - Các công thức cần nhớ
    - Phương pháp giải bài tập
    - Lưu ý an toàn thí nghiệm
    """,
    
    "Sinh học": """
    1. CẤU TRÚC & CHỨC NĂNG:
    - Cấu tạo và đặc điểm
    - Chức năng và vai trò
    - Mối quan hệ cấu trúc-chức năng

    2. QUÁ TRÌNH & CƠ CHẾ:
    - Các quá trình sinh học
    - Cơ chế hoạt động
    - Các yếu tố ảnh hưởng

    3. PHÂN LOẠI & ĐẶC ĐIỂM:
    - Tiêu chí phân loại
    - Đặc điểm nhận dạng
    - So sánh và phân biệt

    4. GHI CHÚ HỌC TẬP:
    - Thuật ngữ chuyên ngành
    - Sơ đồ và hình vẽ quan trọng
    - Câu hỏi trọng tâm
    """,
    
    "Văn học": """
    1. TÁC PHẨM & TÁC GIẢ:
    - Thông tin về tác giả
    - Hoàn cảnh sáng tác
    - Ý nghĩa tác phẩm

    2. PHÂN TÍCH & ĐÁNH GIÁ:
    - Nội dung chính
    - Nghệ thuật đặc sắc
    - Ý nghĩa văn học - xã hội

    3. CHỦ ĐỀ & TƯ TƯỞNG:
    - Chủ đề chính
    - Tư tưởng nổi bật
    - Giá trị nhân văn

    4. GHI CHÚ HỌC TẬP:
    - Dàn ý phân tích
    - Các dẫn chứng tiêu biểu
    - Câu hỏi thảo luận
    """,
    
    "Lịch sử": """
    1. SỰ KIỆN & NHÂN VẬT:
    - Thời gian và địa điểm
    - Nhân vật lịch sử
    - Diễn biến chính

    2. NGUYÊN NHÂN & HỆ QUẢ:
    - Bối cảnh lịch sử
    - Nguyên nhân sự kiện
    - Kết quả và tác động

    3. Ý NGHĨA & ĐÁNH GIÁ:
    - Ý nghĩa lịch sử
    - Bài học kinh nghiệm
    - Đánh giá khách quan

    4. GHI CHÚ HỌC TẬP:
    - Mốc thời gian quan trọng
    - Sơ đồ diễn biến
    - Câu hỏi ôn tập
    """,
    
    "Địa lý": """
    1. ĐẶC ĐIỂM & PHÂN BỐ:
    - Vị trí địa lý
    - Đặc điểm tự nhiên
    - Phân bố không gian

    2. MỐI QUAN HỆ & TÁC ĐỘNG:
    - Quan hệ nhân-quả
    - Tác động qua lại
    - Ảnh hưởng đến đời sống

    3. THỰC TRẠNG & XU HƯỚNG:
    - Hiện trạng phát triển
    - Xu hướng biến đổi
    - Dự báo tương lai

    4. GHI CHÚ HỌC TẬP:
    - Số liệu quan trọng
    - Bản đồ và biểu đồ
    - Các vấn đề thực tế
    """,
    
    "Khác": """
    1. KHÁI NIỆM CHÍNH:
    - Định nghĩa và thuật ngữ
    - Phạm vi áp dụng
    - Ý nghĩa quan trọng

    2. NỘI DUNG TRỌNG TÂM:
    - Các điểm chính
    - Mối liên hệ
    - Ứng dụng thực tế

    3. PHÂN TÍCH & ĐÁNH GIÁ:
    - Ưu điểm và hạn chế
    - So sánh và phân biệt
    - Nhận xét tổng hợp

    4. GHI CHÚ HỌC TẬP:
    - Các điểm cần nhớ
    - Câu hỏi ôn tập
    - Hướng nghiên cứu thêm
    """
}

# Whisper model cache
@st.cache_resource
def load_whisper_model():
    return WhisperModel("small", compute_type="int8")

def transcribe_audio(audio_file):
    try:
        # Lưu file tạm
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as tmp_file:
            tmp_file.write(audio_file.getvalue())
            tmp_path = tmp_file.name

        audio = AudioSegment.from_file(tmp_path)
        os.unlink(tmp_path)

        # Cắt nhỏ từng đoạn 30 giây
        chunk_length_ms = 30 * 1000
        chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

        model = load_whisper_model()
        full_text = ""
        progress = st.progress(0)

        for i, chunk in enumerate(chunks):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as chunk_file:
                chunk.export(chunk_file.name, format="wav")
                segments, _ = model.transcribe(chunk_file.name, language="vi")
                chunk_text = " ".join([seg.text for seg in segments])
                full_text += chunk_text + "\n\n"
                os.unlink(chunk_file.name)

            progress.progress((i + 1) / len(chunks))

        progress.empty()
        return full_text.strip()

    except Exception as e:
        st.error(f"❌ Lỗi khi xử lý file âm thanh lớn: {e}")
        return None

def correct_text(text):
    try:
        model = genai.GenerativeModel('gemini-3.5-flash')
        prompt = f"""
        Hãy sửa lỗi chính tả và cải thiện chất lượng văn bản sau đây, giữ nguyên ý nghĩa nhưng làm cho văn bản mạch lạc và dễ hiểu hơn:

        Văn bản gốc:
        {text}

        Yêu cầu:
        1. Sửa lỗi chính tả và ngữ pháp
        2. Thêm dấu câu phù hợp
        3. Điều chỉnh các từ ngữ không rõ ràng
        4. Giữ nguyên thuật ngữ chuyên môn
        5. Không thay đổi ý nghĩa của văn bản

        Chỉ trả về văn bản đã sửa, không cần giải thích."""
        return model.generate_content(prompt).text.strip()
    except:
        return text

def summarize_text(text, subject):
    try:
        model = genai.GenerativeModel('gemini-3.5-flash')
        template = SUBJECT_TEMPLATES.get(subject, SUBJECT_TEMPLATES["Khác"])
        prompt = f"""Với tư cách là một trợ lý học tập chuyên môn về {subject}, 
        hãy phân tích và tóm tắt nội dung sau đây theo cấu trúc dành cho môn {subject}:

        NỘI DUNG:
        {text}
        
        Hãy tổ chức bản tóm tắt theo cấu trúc sau:
        {template}

        Hãy trình bày rõ ràng, súc tích và dễ hiểu trong 2000 từ bằng tiếng Việt."""
        return model.generate_content(prompt).text.strip()
    except:
        return "Không có tóm tắt"

def generate_title(text, subject):
    try:
        model = genai.GenerativeModel('gemini-3.5-flash')
        prompt = f"""Dựa vào nội dung bài giảng sau đây, hãy tạo một tiêu đề ngắn gọn (tối đa 10 từ) phản ánh chủ đề chính của bài:

        {text[:500]}...

        Lưu ý:
        - Tiêu đề phải ngắn gọn, súc tích
        - Không cần ghi \"Bài giảng về\" hoặc các từ mở đầu tương tự
        - Chỉ trả về tiêu đề, không thêm giải thích"""
        return model.generate_content(prompt).text.strip()
    except:
        return f"Bài ghi {datetime.now().strftime('%d/%m/%Y')}"

# Kết nối SQLite
conn = sqlite3.connect("notes.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS notes (username TEXT, title TEXT, subject TEXT, summary TEXT, content TEXT, timestamp TEXT)''')
conn.commit()

# ====================== Đăng nhập ở Sidebar ======================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

def login_sidebar():
    st.sidebar.title("🔐 Tài khoản")
    username = st.sidebar.text_input("Tên người dùng")
    password = st.sidebar.text_input("Mật khẩu", type="password")
    if st.sidebar.button("Đăng nhập / Đăng ký"):
        user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user:
            if user[1] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.sidebar.success("✅ Đăng nhập thành công")
            else:
                st.sidebar.error("❌ Sai mật khẩu")
        else:
            c.execute("INSERT INTO users VALUES (?, ?)", (username, password))
            conn.commit()
            st.session_state.logged_in = True
            st.session_state.username = username
            st.sidebar.success("✅ Đăng ký và đăng nhập thành công")

if not st.session_state.logged_in:
    login_sidebar()
    st.stop()

# ======================= CHATBOX =======================

def run_chatbox(context_text):
    st.markdown("### 🤖 Hỏi gì về bài giảng này?")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if user_input := st.chat_input("Nhập câu hỏi..."):
        st.chat_message("user").write(user_input)
        model = genai.GenerativeModel("gemini-3.5-flash")
        chat = model.start_chat(history=[
            {"role": "user", "parts": f"Nội dung bài giảng là:\n{context_text}"},
        ])
        response = chat.send_message(user_input)
        st.chat_message("assistant").write(response.text)

        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        
# ==================== RECORD AUDIO ====================
audio_queue = queue.Queue()
recorded_audio_path = "recorded_audio.wav"

# Chế độ hiển thị hội thoại
st.sidebar.markdown("### ⚙️ Tuỳ chọn")
chat_mode = st.sidebar.radio("Chế độ hiển thị văn bản", ["Hội thoại (Người 1/2)", "Thông thường"])

class AudioProcessor:
    def __init__(self):
        self.frames = []
        self.partial_text = ""
        self.model = load_whisper_model()
        self.speaker_index = 1

    def recv(self, frame):
        audio = frame.to_ndarray()
        self.frames.append(audio)

        if len(self.frames) >= 5:
            audio_data = np.concatenate(self.frames[-5:])
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                with wave.open(tmp.name, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(48000)
                    wf.writeframes(audio_data.tobytes())
                try:
                    segments, _ = self.model.transcribe(tmp.name, language="vi")
                    for seg in segments:
                        if chat_mode == "Hội thoại (Người 1/2)":
                            self.partial_text += f"\n👤 Người {self.speaker_index}: {seg.text.strip()}"
                            self.speaker_index = 2 if self.speaker_index == 1 else 1
                        else:
                            self.partial_text += f" {seg.text.strip()}"
                except:
                    pass

        return frame

    def save_audio(self):
        if self.frames:
            audio_data = np.concatenate(self.frames)
            with wave.open(recorded_audio_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(audio_data.tobytes())
            return recorded_audio_path
        return None

ctx = webrtc_streamer(
    key="mic",
    mode=WebRtcMode.SENDONLY,
    client_settings=ClientSettings(media_stream_constraints={"audio": True, "video": False}),
    audio_receiver_size=256,
    async_processing=False,
)

if ctx and ctx.audio_receiver:
    if "audio_processor" not in st.session_state:
        st.session_state.audio_processor = AudioProcessor()

    def collect_audio():
        while True:
            try:
                frame = ctx.audio_receiver.get_frame(timeout=1)
                st.session_state.audio_processor.recv(frame)
                st.session_state.partial_transcript = st.session_state.audio_processor.partial_text
            except queue.Empty:
                break

    t = threading.Thread(target=collect_audio)
    t.start()

    st.markdown("### 📝 Đang ghi âm...")
    st.info(st.session_state.get("partial_transcript", "(Đang xử lý...)"))

    if st.button("⏹ Dừng và xử lý ghi âm"):
        audio_file_path = st.session_state.audio_processor.save_audio()
        if audio_file_path:
            with open(audio_file_path, "rb") as f:
                transcript_text = transcribe_audio(f)
                if transcript_text:
                    st.subheader("📄 Văn bản từ ghi âm trực tiếp")
                    st.write(transcript_text)
                    corrected = correct_text(transcript_text)
                    summary = summarize_text(corrected, subject)
                    title = generate_title(corrected, subject)

                    st.subheader("✍️ Tóm tắt")
                    st.write(summary)

                    if st.button("💾 Lưu ghi chú từ ghi âm"):
                        c.execute("INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?)",
                                  (st.session_state.username, title, subject, summary, corrected, datetime.now().isoformat()))
                        conn.commit()
                        st.success("✅ Đã lưu ghi chú từ ghi âm!")

# ======================= MAIN UI =======================
# Giao diện Streamlit
st.set_page_config(page_title="NoteBot", layout="wide")
st.title(" NoteBot")

# Hướng dẫn sử dụng
with st.expander("❓ Hướng dẫn sử dụng"):
    st.markdown("""
    ### 📘 Hướng dẫn sử dụng NoteBot

    #### Bước chuẩn bị:
    1. Truy cập [https://www.notion.com/my-integrations](https://www.notion.com/my-integrations) để tạo Notion Integration Token
    2. Lấy Notion Token (bắt đầu bằng secret_...)
    3. Tạo một database trong Notion với các cột sau: `Title` (kiểu Title), `Subject` (Rich text), `Summary` (Rich text), `Date` (Date)
    4. Trong Integration mới tạo, chọn mục Access -> Edit access -> Chọn Teamspaces -> Chọn Workspace của bạn -> Chọn Database vừa mới tạo
    5. Lấy Database ID trong link của Database vừa tạo (Bắt đầu từ sau dấu "/" đến dấu "?" hoặc đến hết)

    #### Cách sử dụng ứng dụng:
    1. Nhập Notion Token và Database ID vào thanh bên trái → Nhấn "Lưu thông tin"
    2. Chọn môn học phù hợp
    3. Tải lên file ghi âm định dạng `.mp3` hoặc `.wav`
    4. Nhấn "Tạo ghi chú và lưu vào Notion"

    #### Ứng dụng sẽ tự động:
    - Chuyển âm thanh thành văn bản
    - Sửa lỗi chính tả và cải thiện chất lượng văn bản
    - Tóm tắt theo cấu trúc từng môn học
    - Tạo tiêu đề ngắn gọn phản ánh nội dung chính
    - Lưu toàn bộ ghi chú vào tài khoản Notion của bạn

    """)

# Nhập token và database
with st.sidebar:
    st.image("https://raw.githubusercontent.com/TrNghia16509/NoteBot/main/logo%20Notebot.jpg", width=150)

# Điều kiện để tiếp tục
if "notion_token" in st.session_state and "notion_db_id" in st.session_state:
    col1, col2 = st.columns([2, 1])

    with col1:
        subject = st.selectbox("Chọn môn học", ["Toán học", "Vật lý", "Hóa học", "Sinh học", "Văn học", "Lịch sử", "Địa lý", "Khác"])
        audio_file = st.file_uploader("📤 Tải lên file âm thanh (.mp3 hoặc .wav)", type=["mp3", "wav"])


        if audio_file and st.button("Tạo ghi chú"):

            with st.spinner("Chuyển đổi âm thanh..."):
                text = transcribe_audio(audio_file)
                

            if text:
                st.subheader("📄 Văn bản trích xuất")
                st.write(transcript_text)

                corrected = correct_text(transcript_text)
                summary = summarize_text(corrected, subject)
                title = generate_title(corrected, subject)

                st.subheader("✍️ Tóm tắt")
                st.write(summary)

                if st.button("💾 Lưu ghi chú"):
                    c.execute("INSERT INTO notes VALUES (?, ?, ?, ?, ?, ?)",
                        (st.session_state.username, title, subject, summary, corrected, datetime.now().isoformat()))
                    conn.commit()
                    st.success("✅ Đã lưu ghi chú!")



    with col2:
        st.subheader("📚 Ghi chú đã lưu")
        notes = c.execute("SELECT title, subject, summary, timestamp FROM notes WHERE username=? ORDER BY timestamp DESC", (st.session_state.username,)).fetchall()
        if notes:
            for note in notes:
                with st.expander(f"📝 {note[0]} ({note[1]}) - {note[3][:10]}"):
                    st.write(note[2])
        else:
            st.info("Chưa có ghi chú nào được lưu.")
else:
    st.warning("⚠️ Vui lòng đăng nhập để sử dụng ứng dụng.")
