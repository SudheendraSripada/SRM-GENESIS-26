FROM python:3.11-slim

WORKDIR /workspace

# Install system utilities and dependencies for k6
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install official k6 binary
RUN curl -s https://dl.k6.io/key.gpg | gpg --dearmor -o /usr/share/keyrings/k6-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | tee /etc/apt/sources.list.d/k6.list && \
    apt-get update && apt-get install -y k6 && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    aiosqlite \
    sse-starlette \
    httpx \
    pytest \
    anyio \
    python-dotenv \
    crewai \
    crewai-tools

COPY agents/ /workspace/agents/
COPY validator/ /workspace/validator/
COPY orchestrator/ /workspace/orchestrator/

ENV PYTHONPATH="/workspace:/workspace/agents/src:/workspace/validator"
ENV VALIDATOR_URL="http://validator:8000"
ENV K6_PATH="/usr/bin/k6"

EXPOSE 8001

CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8001"]

