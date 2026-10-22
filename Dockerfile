FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 10001 app
COPY pyproject.toml README.md ./
COPY skilldraft ./skilldraft
COPY data/taxonomy.json ./data/taxonomy.json
COPY models/scorer.hashing-v1.json models/scorer.cv.hashing-v1.json ./models/
COPY prompts ./prompts
RUN pip install --no-cache-dir . && mkdir -p /app/var && chown app /app/var
USER app
ENV SKILLDRAFT_FEEDBACK_LOG=/app/var/feedback.jsonl PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "skilldraft", "serve", "--host", "0.0.0.0", "--port", "8080"]
