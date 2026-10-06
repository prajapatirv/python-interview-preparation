# Local Docker run (build context = the repo root, see docker-compose.yml).
# The examples folder is mounted at /prep at run time, so edits to examples show up without a rebuild.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY pyprep-live/requirements.txt pyprep-live/requirements-examples.txt ./
RUN pip install -r requirements.txt -r requirements-examples.txt

COPY pyprep-live/app ./app
COPY pyprep-live/static ./static

ENV PREP_ROOT=/prep
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
