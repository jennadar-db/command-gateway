FROM python:3.12-slim

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST

# Proxy vars are set only during build for pip/apt. They are NOT persisted
# into the runtime image ENV so Cloud Run can reach GCP metadata and
# downstream services without a corporate proxy.
COPY gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r /app/requirements.txt


COPY gateway /app/gateway

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["python", "-m", "gateway.server"]
