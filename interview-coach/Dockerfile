# Optional local Docker run (build context = the workspace root, see docker-compose.yml).
# The default is a native run: start.cmd / ./start.sh. Docker: start.cmd docker / ./start.sh docker.
# The workspace (java/, python/ and this app's skills/) is mounted at /content at run time, so content
# edits show up without a rebuild; saved questions are written back into it.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY shared/prepkit /tmp/prepkit
COPY interview-coach/requirements.txt ./
RUN pip install /tmp/prepkit -r requirements.txt && rm -rf /tmp/prepkit

COPY interview-coach/app ./app
COPY interview-coach/static ./static
COPY interview-coach/evals ./evals

ENV COACH_ROOT=/content COACH_SKILLS=/content/interview-coach/skills COACH_DATA=/data
EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
