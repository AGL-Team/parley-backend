ARG PYTHON_VERSION=3.13-slim
FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system parley \
    && adduser --system --ingroup parley parley

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

USER parley

EXPOSE 8000

CMD ["uvicorn", "parley.main:app", "--host", "0.0.0.0", "--port", "8000"]
