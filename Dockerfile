FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg unixodbc-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir poetry==1.8.4
COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-root
COPY . .
RUN poetry install --only main
EXPOSE 8501 8503
CMD ["sh", "-c", "uvicorn DataDictionaryAdminApp.api.swagger_app:app --host 0.0.0.0 --port 8503 & streamlit run src/DataDictionaryAdminApp/streamlit_app.py --server.address 0.0.0.0 --server.port 8501"]
