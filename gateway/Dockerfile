FROM python:3.12-slim

WORKDIR /app

COPY gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY gateway /app/gateway

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["python", "-m", "gateway.server"]
