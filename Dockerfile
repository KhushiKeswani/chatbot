FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --prefix=/install \
    -r requirements.txt


FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY . .

EXPOSE 8000

CMD ["uvicorn","bot:api","--host","0.0.0.0","--port","8000"]