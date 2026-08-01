# Minimal single-stage image for the long-polling bot process.
# No public port is exposed — Telegram is reached via outbound long-poll
# only (ADR-0034 §Q4). Coolify service wiring itself is an infra/ops
# concern outside this file's scope.
FROM python:3.12-slim

WORKDIR /app

# FR-BOT-003: libzbar0 is required by pyzbar for QR code decoding (/scan command).
RUN apt-get update && apt-get install -y --no-install-recommends libzbar0 && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

CMD ["python", "-m", "src.main"]
