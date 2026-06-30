FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Gateway listens on 8090; nginx/tunnel terminates TLS in front of it.
EXPOSE 8090
CMD ["uvicorn", "gateway:app", "--host", "0.0.0.0", "--port", "8090"]
