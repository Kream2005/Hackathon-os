"""
Web UI Service — STUB backend for the dashboard
Port: 8080
Personne 3 will implement the full frontend.
This serves as a simple API gateway / proxy and static health endpoint.
"""

import time
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response, HTMLResponse

app = FastAPI(title="Web UI Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics
PAGE_VIEWS = Counter(
    "webui_page_views_total",
    "Total page views",
    ["page"],
)
REQUEST_LATENCY = Histogram(
    "webui_request_duration_seconds",
    "Request latency",
    ["endpoint"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "web-ui",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", response_class=HTMLResponse)
def index():
    PAGE_VIEWS.labels(page="index").inc()
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Incident Platform</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0f172a;
                color: #e2e8f0;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .container {
                text-align: center;
                padding: 2rem;
            }
            h1 {
                font-size: 2.5rem;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, #3b82f6, #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .status {
                display: inline-block;
                padding: 0.5rem 1.5rem;
                background: #059669;
                border-radius: 9999px;
                font-weight: 600;
                margin: 1rem 0;
            }
            .services {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
                margin-top: 2rem;
                max-width: 800px;
            }
            .service-card {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 0.75rem;
                padding: 1.5rem;
                transition: transform 0.2s;
            }
            .service-card:hover { transform: translateY(-2px); }
            .service-card h3 { color: #3b82f6; margin-bottom: 0.5rem; }
            .service-card a {
                color: #94a3b8;
                text-decoration: none;
                font-size: 0.875rem;
            }
            .service-card a:hover { color: #e2e8f0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚨 Incident Platform</h1>
            <div class="status">✅ All Systems Operational</div>
            <p style="margin-top: 1rem; color: #94a3b8;">
                Mini PagerDuty Clone — Hackathon Project
            </p>
            <div class="services">
                <div class="service-card">
                    <h3>Alert Ingestion</h3>
                    <a href="http://localhost:8001/health" target="_blank">:8001/health</a><br>
                    <a href="http://localhost:8001/docs" target="_blank">:8001/docs</a>
                </div>
                <div class="service-card">
                    <h3>Incident Management</h3>
                    <a href="http://localhost:8002/health" target="_blank">:8002/health</a><br>
                    <a href="http://localhost:8002/docs" target="_blank">:8002/docs</a>
                </div>
                <div class="service-card">
                    <h3>On-Call Service</h3>
                    <a href="http://localhost:8003/health" target="_blank">:8003/health</a><br>
                    <a href="http://localhost:8003/docs" target="_blank">:8003/docs</a>
                </div>
                <div class="service-card">
                    <h3>Notification</h3>
                    <a href="http://localhost:8004/health" target="_blank">:8004/health</a><br>
                    <a href="http://localhost:8004/docs" target="_blank">:8004/docs</a>
                </div>
                <div class="service-card">
                    <h3>Prometheus</h3>
                    <a href="http://localhost:9090" target="_blank">:9090</a>
                </div>
                <div class="service-card">
                    <h3>Grafana</h3>
                    <a href="http://localhost:3000" target="_blank">:3000</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
