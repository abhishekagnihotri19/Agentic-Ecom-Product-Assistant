FROM python:3.11-slim

WORKDIR /app

# install system deps
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# install python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app
COPY . .

EXPOSE 8001

CMD ["uvicorn", "prod_assistant.router.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]