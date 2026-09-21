# RiskGraph EU API — build from the REPOSITORY ROOT:  docker build -f backend/Dockerfile -t riskgraph-api .
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
# LightGBM needs the OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
# Only what the API imports: the API package, the numpy-only decision/reasons modules, and the built bundle.
COPY backend/app backend/app
COPY riskgraph/__init__.py riskgraph/config.py riskgraph/decision.py riskgraph/reasons.py riskgraph/
COPY artifacts/demo artifacts/demo
RUN useradd --create-home --uid 10001 app && chown -R app /srv
USER app
ENV RISKGRAPH_BUNDLE_DIR=/srv/artifacts/demo RISKGRAPH_DB_PATH=/tmp/riskgraph_decisions.db RISKGRAPH_DEMO_MODE=true
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:%s/health'%os.environ.get('PORT','8000'))"
CMD ["sh", "-c", "uvicorn backend.app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
