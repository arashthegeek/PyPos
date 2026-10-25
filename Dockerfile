FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY app/ .

RUN pip install --no-cache-dir --default-timeout=180 -r requirements.txt

EXPOSE 8000

CMD ["python", "app.py"]

