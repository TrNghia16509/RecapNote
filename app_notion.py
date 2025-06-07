import streamlit as st
from notion_client import Client
from datetime import datetime
import whisper
import tempfile
import os
import google.generativeai as genai
from dotenv import load_dotenv
from pydub import AudioSegment
import tempfile


# Load môi trường cho Gemini
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
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
    return whisper.load_model("medium")

def transcribe_audio_chunks(audio_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.name)[1]) as tmp_file:
            tmp_file.write(audio_file.getvalue())
            tmp_path = tmp_file.name

        audio = AudioSegment.from_file(tmp_path)
        chunk_len_ms = 60000  # 60 giây
        chunks = [audio[i:i+chunk_len_ms] for i in range(0, len(audio), chunk_len_ms)]
        model = load_whisper_model()

        full_text = ""
        
        for idx, chunk in enumerate(chunks):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as chunk_file:
                chunk_path = chunk_file.name

            # Sau khi thoát khối `with`, file đã được tạo nhưng không còn bị giữ bởi Python
            chunk.export(chunk_path, format="mp3")

            st.write(f"🎧 Đang xử lý đoạn {idx+1}/{len(chunks)}...")
            result = model.transcribe(chunk_path, language="vi")

            full_text += result["text"] + "\\n\\n"
            os.unlink(chunk_path)  # Xóa file tạm sau khi xong

        os.unlink(tmp_path)
        return full_text.strip()
    except Exception as e:
        st.error(f"❌ Không thể chuyển âm thanh thành văn bản: {e}")
        return None

def correct_text(text):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
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
        model = genai.GenerativeModel('gemini-2.0-flash')
        template = SUBJECT_TEMPLATES.get(subject, SUBJECT_TEMPLATES["Khác"])
        prompt = f"""Với tư cách là một trợ lý học tập chuyên môn về {subject}, 
        hãy phân tích và tóm tắt nội dung sau đây theo cấu trúc dành cho môn {subject}:

        NỘI DUNG:
        {text}
        
        Hãy tổ chức bản tóm tắt theo cấu trúc sau:
        {template}

        Hãy trình bày rõ ràng, súc tích và dễ hiểu bằng tiếng Việt."""
        return model.generate_content(prompt).text.strip()
    except:
        return ""

def generate_title(text, subject):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""Dựa vào nội dung bài giảng sau đây, hãy tạo một tiêu đề ngắn gọn (tối đa 10 từ) phản ánh chủ đề chính của bài:

        {text[:500]}...  # Chỉ lấy 500 ký tự đầu để tạo tiêu đề

        Lưu ý:
        - Tiêu đề phải ngắn gọn, súc tích
        - Không cần ghi "Bài giảng về" hoặc các từ mở đầu tương tự
        - Chỉ trả về tiêu đề, không thêm giải thích"""
        return model.generate_content(prompt).text.strip()
    except:
        return f"Bài ghi {datetime.now().strftime('%d/%m/%Y')}"

def save_to_notion(notion_token, database_id, subject, content, summary):
    notion = Client(auth=notion_token)
    title = generate_title(content, subject)
    now = datetime.now().isoformat()

    try:
        response = notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Title": {"title": [{"text": {"content": title}}]},
                "Subject": {"rich_text": [{"text": {"content": subject}}]},
                "Summary": {"rich_text": [{"text": {"content": summary[:2000]}}]},
                "Date": {"date": {"start": now}},
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": content[:2000]}}]}
                }
            ]
        )
        st.success("✅ Ghi chú đã được gửi tới Notion.")
        return True
    except Exception as e:
        st.error("❌ Không thể ghi chú vào Notion.")
        st.exception(e)  # In lỗi chi tiết
        return False

def load_notes_from_notion(notion_token, database_id):
    notion = Client(auth=notion_token)
    try:
        query = notion.databases.query(database_id=database_id, sorts=[{"timestamp": "created_time", "direction": "descending"}])
        pages = query.get("results", [])
        notes = []
        for page in pages:
            props = page.get("properties", {})
            notes.append({
                "title": props.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", "(Không có tiêu đề)"),
                "subject": props.get("Subject", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "summary": props.get("Summary", {}).get("rich_text", [{}])[0].get("text", {}).get("content", ""),
                "date": props.get("Date", {}).get("date", {}).get("start", "")
            })
        return notes
    except Exception as e:
        st.error(f"Không thể tải ghi chú từ Notion: {e}")
        return []

# Giao diện Streamlit
st.set_page_config(page_title="NoteBot", layout="wide")
st.title("📝 NoteBot")

# Hướng dẫn sử dụng
with st.expander("❓ Hướng dẫn sử dụng"):
    st.markdown("""
    ### 📘 Hướng dẫn sử dụng NoteBot

    #### Bước chuẩn bị:
    1. Truy cập [https://www.notion.com/my-integrations](https://www.notion.com/my-integrations) để tạo Notion Integration Token
    2. Tạo một database trong Notion với các cột sau: `Title`, `Subject`, `Summary`, `Date`
    3. Chia sẻ quyền truy cập cho integration vừa tạo vào database đó

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
    st.header("🔗 Kết nối Notion của bạn")
    notion_token = st.text_input("Notion Token", type="password", value=st.session_state.get("notion_token", ""))
    database_id = st.text_input("Notion Database ID", value=st.session_state.get("notion_db_id", ""))

    if st.button("Lưu thông tin"):
        st.session_state.notion_token = notion_token
        st.session_state.notion_db_id = database_id
        st.success("Đã lưu cấu hình Notion.")

# Điều kiện để tiếp tục
if "notion_token" in st.session_state and "notion_db_id" in st.session_state:
    col1, col2 = st.columns([2, 1])

    with col1:
        subject = st.selectbox("Chọn môn học", ["Toán học", "Vật lý", "Hóa học", "Sinh học", "Văn học", "Lịch sử", "Địa lý", "Khác"])
        audio_file = st.file_uploader("Tải file ghi âm", type=["mp3", "wav"])


        if audio_file and st.button("Tạo ghi chú và lưu vào Notion"):

            with st.spinner("Chuyển đổi âm thanh..."):
                text = transcribe_audio_chunks(audio_file)
                

            if text:
                st.write("📄 Văn bản được tạo")
                with st.spinner("Sửa lỗi và tạo tóm tắt..."):
                    corrected = correct_text(text)
                    summary = summarize_text(corrected, subject)
                st.write("🧠 Tóm tắt xong")

                st.subheader("✏️ Văn bản đã sửa")
                st.subheader("📌 Tóm tắt")

                if save_to_notion(st.session_state.notion_token, st.session_state.notion_db_id, subject, corrected, summary):
                    st.success("✅ Đã lưu ghi chú vào Notion!")
                else:
                    st.error("❌ Không thể lưu ghi chú vào Notion!")


    with col2:
        st.subheader("📚 Ghi chú đã lưu trong Notion")
        notes = load_notes_from_notion(st.session_state.notion_token, st.session_state.notion_db_id)
        if notes:
            for note in notes:
                with st.expander(f"{note['title']} ({note['subject']}) - {note['date']}"):
                    st.write("**Tóm tắt:**")
                    st.write(note['summary'])
        else:
            st.info("Chưa có ghi chú nào được lưu trong Notion.")
else:
    st.warning("⚠️ Vui lòng nhập và lưu Notion Token & Database ID để sử dụng ứng dụng.")
