# Optional local Docker run (build context = the workspace root, see docker-compose.yml).
# The default is a native run: start.cmd / ./start.sh. Docker: start.cmd docker / ./start.sh docker.
# The examples folder is mounted at /prep at run time, so edits to examples show up without a rebuild.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY shared/prepkit /tmp/prepkit
COPY python/pyprep-live/requirements.txt python/pyprep-live/requirements-examples.txt ./
RUN pip install /tmp/prepkit -r requirements.txt -r requirements-examples.txt && rm -rf /tmp/prepkit

COPY python/pyprep-live/app ./app
COPY python/pyprep-live/static ./static

ENV PREP_ROOT=/prep
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
