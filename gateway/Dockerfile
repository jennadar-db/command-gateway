FROM python:3.12-slim

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST

ENV HTTP_PROXY=${HTTP_PROXY} \
	HTTPS_PROXY=${HTTPS_PROXY} \
	NO_PROXY=${NO_PROXY} \
	PIP_INDEX_URL=${PIP_INDEX_URL} \
	PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

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
