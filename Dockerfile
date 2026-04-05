FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY app /app/app
COPY docs /app/docs

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn hoiku_plan_writer.main:app --host 0.0.0.0 --port ${PORT:-8000}"]