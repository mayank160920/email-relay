FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py relay.py ./

# Port 25 for inbound SMTP
EXPOSE 25

# Run directly (no sudo needed - Docker runs as root by default)
CMD ["python3", "relay.py"]
