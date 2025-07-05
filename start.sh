#!/bin/bash
# start.sh

# Chạy Flask backend ở cổng 8000
gunicorn main_app:flask_app --bind 0.0.0.0:8000 &
# Chạy Streamlit app
streamlit run main_app.py --server.port 10000
