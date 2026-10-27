ARG PYTHON_IMAGE=python:3.14.8-slim-bookworm@sha256:48b13b003dda20b16f9442b8475aa05fe21bf6579a8c881db92ffb4d8fd20f83
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /workspace
COPY requirements.lock requirements.lock
RUN pip install --only-binary=:all: --no-cache-dir --require-hashes -r requirements.lock && groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home app
COPY . .
USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--no-control-socket", "--workers", "1", "--threads", "2", "--timeout", "20", "--access-logfile", "/dev/null", "--error-logfile", "-"]
