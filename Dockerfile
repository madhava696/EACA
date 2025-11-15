# syntax=docker/dockerfile:1

##########################
# Build stage
##########################
FROM python:3.10.11-slim AS build

ARG MODE=web
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=off \
    PYTHONUNBUFFERED=1 \
    MODE=${MODE}

# Install system deps required by many ML + image packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ca-certificates \
    libglib2.0-0 libsm6 libxext6 libxrender-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency lists early for caching
COPY requirements.txt /app/requirements.txt
# Optionally allow a separate worker requirements file
COPY requirements-worker.txt /app/requirements-worker.txt

# Upgrade pip wheel tools
RUN pip install --upgrade pip setuptools wheel

# If building a worker image, install cpu PyTorch wheels from PyTorch CPU index,
# then install worker requirements; else install regular requirements only.
RUN if [ "$MODE" = "worker" ]; then \
      echo "=== Installing torch (CPU) + worker requirements ===" && \
      pip install --index-url https://download.pytorch.org/whl/cpu/ \
        "torch==2.2.2" "torchvision==0.17.2" || true && \
      pip install -r requirements-worker.txt ; \
    else \
      echo "=== Installing web (light) requirements ===" && \
      pip install -r requirements.txt ; \
    fi

# (Optional) If your requirements list includes opencv-contrib-python, ensure headless is used.
# The above requirements files should prefer opencv-contrib-python-headless.

##########################
# Runtime stage - small final image
##########################
FROM python:3.10.11-slim

ENV PYTHONUNBUFFERED=1 \
    MODE=${MODE} \
    PORT=8080

# Minimal runtime deps for image libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed site-packages from build
COPY --from=build /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

# Copy app code
COPY . /app

# copy start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create non-root user and give ownership
RUN useradd --create-home appuser \
  && chown -R appuser:appuser /app
USER appuser

EXPOSE ${PORT}

# Recommended to run with a healthcheck on your hosting platform
CMD ["/app/start.sh"]
