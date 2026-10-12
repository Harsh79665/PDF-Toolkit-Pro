FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source tree
COPY . .

# Expose web application port
EXPOSE 5000

ENV HOST=0.0.0.0
ENV PORT=5000
ENV DEBUG=false

# Run application
CMD ["python", "app.py"]
