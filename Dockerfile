FROM python:3.12-slim

RUN apt update && apt install -yq tzdata libpq-dev gcc

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]