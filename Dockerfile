FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir numpy scipy pydantic fastapi uvicorn scikit-learn plotly httpx

COPY src/ src/

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["uvicorn", "theranostics.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
