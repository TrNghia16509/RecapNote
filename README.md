# 📘 NoteBot - Ghi chú bài giảng vào Notion

**NoteBot** là một ứng dụng Streamlit giúp bạn:
- Tải file ghi âm (.mp3 hoặc .wav)
- Tự động chuyển thành văn bản bằng Whisper
- Sửa lỗi chính tả và cải thiện câu văn bằng Gemini
- Tóm tắt nội dung theo từng môn học
- Lưu toàn bộ vào Notion cá nhân (có tiêu đề, ngày, nội dung, tóm tắt)

---

## 🚀 Cách sử dụng

### 1. Chuẩn bị Notion
- Vào [https://www.notion.com/my-integrations](https://www.notion.com/my-integrations)
- Tạo Integration mới và lấy **Notion Token** (bắt đầu bằng `secret_...`)
- Tạo một **Database** trong Notion với các cột:
  - `Title` (kiểu Title)
  - `Subject` (Rich text)
  - `Summary` (Rich text)
  - `Date` (Date)
- Trong Integration mới tạo, chọn mục Access -> Edit access -> Chọn Teamspaces -> Chọn Workspace của bạn -> Chọn Database vừa mới tạo
- Lấy **Database ID** trong link của **Database** (Bắt đầu từ sau dấu "/" đến dấu "?" hoặc đến hết)

### 2. Cài đặt và chạy app

```bash
git clone https://github.com/your_username/notebot-notion.git
cd notebot-notion
pip install -r requirements.txt
streamlit run app_notion.py
```

---

## 📦 Thư viện sử dụng

- `streamlit` - giao diện web
- `whisper` - chuyển âm thanh thành văn bản
- `pydub` - chia nhỏ file âm thanh
- `google-generativeai` - sửa và tóm tắt văn bản bằng Gemini
- `notion-client` - lưu dữ liệu vào Notion
- `ffmpeg` - xử lý định dạng âm thanh (cần cài ngoài)

---

## 💡 Gợi ý sử dụng

- Dùng file thu âm giọng nói rõ ràng, định dạng `.mp3` hoặc `.wav`
- Có thể xem lại toàn bộ ghi chú đã lưu trong Notion ngay trong ứng dụng

