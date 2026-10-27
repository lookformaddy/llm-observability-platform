FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY llm_observability/ ./llm_observability/
COPY tests/ ./tests/
EXPOSE 8000
CMD ["uvicorn", "llm_observability.service:app", "--host", "0.0.0.0", "--port", "8000"]
