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

COPY agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r /app/requirements.txt


COPY agent /app/agent

ENV MCP_URL=http://command-gateway:8000/mcp
ENV REQUESTOR_URL=https://command-gateway-demo.local/requestor

CMD ["python", "-m", "agent.runner"]
