
FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.4.2

WORKDIR /workspace

COPY test_math.py .

USER 10001:10001

CMD ["python", "-m", "pytest", "-v", "/workspace/test_math.py"]
