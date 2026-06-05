FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for grpc_health_probe and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install grpc_health_probe
RUN GRPC_HEALTH_PROBE_VERSION=v0.4.24 && \
    ARCH=$(uname -m) && \
    case $ARCH in \
        x86_64) BIN_ARCH=amd64 ;; \
        aarch64) BIN_ARCH=arm64 ;; \
        *) echo "unsupported arch: $ARCH"; exit 1 ;; \
    esac && \
    curl -sSL "https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-${BIN_ARCH}" -o /usr/local/bin/grpc_health_probe && \
    chmod +x /usr/local/bin/grpc_health_probe

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy application code (mounted at runtime for dev, baked in for prod)
COPY . .

EXPOSE 50051

CMD ["python", "server.py"]
