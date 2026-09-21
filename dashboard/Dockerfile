FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[dashboard]"
COPY dashboard/app.py ./dashboard/app.py
EXPOSE 8501
# Cloud Run injecte PORT (8080 par défaut). En local, Streamlit conserve son port 8501.
CMD ["sh", "-c", "exec streamlit run dashboard/app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.headless=true"]
