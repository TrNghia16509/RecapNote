FROM python:3.10-slim

WORKDIR /app

# Cài các gói hệ thống cần thiết
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt và cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Copy toàn bộ source code, bao gồm start.sh
COPY . .

# ✅ Gán quyền thực thi sau khi đã copy
RUN chmod +x start.sh

EXPOSE 10000

# ✅ Gọi file start.sh để chạy app
CMD ["start.sh"]
