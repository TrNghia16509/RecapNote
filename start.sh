#!/bin/bash

# Cấp quyền thực thi (đảm bảo nếu chạy độc lập)
chmod +x start.sh

# Chạy backend Flask ở cổng 8000
python3 -u main_app.py &

# Đợi Flask khởi động trong nền
sleep 5

# Chạy Streamlit ở cổng 10000 (hoặc bất kỳ cổng nào bạn chọn)
streamlit run main_app.py --server.port=10000 --server.enableCORS=false
