FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY app ./app
COPY configs ./configs
COPY scripts ./scripts

# Run the application as an unprivileged service account in every container.
RUN addgroup --system app && adduser --system --ingroup app --home /home/app app \
    && chown -R app:app /app /home/app
USER app
ENV HOME=/home/app

EXPOSE 8000 8501
