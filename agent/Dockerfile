FROM python:3.12-slim

WORKDIR /app

COPY agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY agent /app/agent

ENV MCP_URL=http://command-gateway:8000/mcp
ENV REQUESTOR_URL=https://command-gateway-demo.local/requestor

CMD ["python", "-m", "agent.runner"]
