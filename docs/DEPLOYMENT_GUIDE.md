# Deployment Guide

## Local installation

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

## Start backend

    $env:SIH_TELEMETRY_MODE = "mock"
    python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000

Verify with GET /api/v1/health and GET /api/v1/ready.

## Start dashboard

In another terminal:

    $env:SIH_API_URL = "http://127.0.0.1:8000"
    python -m streamlit run app\streamlit_app.py

Select Full Integrated Demo. The dashboard calls the backend demo endpoint;
the backend composes the existing engine.

## Docker Compose

    docker compose up --build

The compose stack contains backend and dashboard, mounts model/config/demo
artifacts read-only, and writes audit output to the local ignored results path.
Raw/processed datasets and PCAPs are not copied into the image.

## Authenticated development

Set SIH_AUTH_ENABLED=true and inject role tokens through the environment. Use
Authorization: Bearer token. Do not put tokens in compose files, source, or
logs.

