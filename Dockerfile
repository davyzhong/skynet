FROM python:3.11-slim

WORKDIR /app

# Copy pyproject.toml and install dependencies without installing the package
COPY pyproject.toml .
RUN pip install fastapi uvicorn polars sqlalchemy asyncpg celery redis pydantic pydantic-settings httpx openpyxl plotly anthropic python-multipart alembic python-dotenv pyyaml

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
