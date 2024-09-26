FROM python:3.9-slim as base

# build and load all requirements
FROM base as builder
WORKDIR /airbyte/integration_code

ENV GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
ENV GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1

# Upgrade pip and install necessary build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libffi-dev \
    wget \
    && pip install --upgrade pip

COPY setup.py ./
# Install necessary packages to a temporary folder, including google-ads
RUN pip install --prefix=/install . google-ads

# Build a clean environment
FROM base
WORKDIR /airbyte/integration_code

# Copy all loaded and built libraries to a pure basic image
COPY --from=builder /install /usr/local
# Add default timezone settings
COPY --from=builder /usr/share/zoneinfo/Etc/UTC /etc/localtime
RUN echo "Etc/UTC" > /etc/timezone

# Bash is installed for more convenient debugging
RUN apt-get update && apt-get install -y bash

# Copy payload code only
COPY main.py ./
COPY destination_google_ads ./destination_google_ads

ENV AIRBYTE_ENTRYPOINT "python /airbyte/integration_code/main.py"
ENTRYPOINT ["python", "/airbyte/integration_code/main.py"]

LABEL io.airbyte.version=0.1.0
LABEL io.airbyte.name=airbyte/destination-google-ads
