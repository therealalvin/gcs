FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY gcs.py .
CMD ["python", "gcs.py"]
