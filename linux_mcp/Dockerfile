FROM python:3.12-slim

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=${NO_PROXY}
ENV http_proxy=${http_proxy}
ENV https_proxy=${https_proxy}
ENV no_proxy=${no_proxy}

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    procps \
    iputils-ping \
    dnsutils \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY linux_mcp/requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip && \
    (python -m pip install --no-cache-dir -r /app/requirements.txt || \
     python -m pip install --no-cache-dir \
       --trusted-host pypi.org \
       --trusted-host files.pythonhosted.org \
       --trusted-host pypi.python.org \
       -r /app/requirements.txt)

COPY linux_mcp /app/linux_mcp

EXPOSE 9001

CMD ["python", "linux_mcp/server.py"]