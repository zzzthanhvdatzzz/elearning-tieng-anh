FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p data/uploads data/out/weekly
VOLUME ["/app/data"]

EXPOSE 8000
# 1 worker: SQLite + thread báo cáo tuần chạy trong cùng tiến trình (mục 3.1).
# Nhiều worker sẽ sinh trùng thư tuần nếu chưa tách job ra dịch vụ riêng.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
