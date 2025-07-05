# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements before code (cache install)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Cấp quyền thực thi cho script start.sh
RUN chmod +x start.sh

# Set environment variable
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# Chạy file start.sh
CMD ["./start.sh"]
