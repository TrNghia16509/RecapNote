# Base image: Python + system dependencies
FROM python:3.10-slim

# Install OS dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose default Streamlit port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "main_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
