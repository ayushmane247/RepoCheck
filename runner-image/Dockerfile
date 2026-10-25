
FROM python:3.12-slim

RUN pip install --no-cache-dir \
    pytest==8.4.2 \
    fastapi==0.121.3 \
    httpx==0.28.1 \
    PyYAML==6.0.2

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
ENV HOME=/tmp

WORKDIR /workspace

USER 10001:10001

CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "/workspace"]
