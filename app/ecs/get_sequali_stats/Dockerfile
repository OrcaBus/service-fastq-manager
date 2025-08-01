FROM ubuntu:noble

ARG TARGETPLATFORM
ARG SEQUALI_VERSION="1.0.1"
ARG PYARROW_VERSION="20.0.0"
ARG PANDAS_VERSION="2.3.1"
ARG MULTIQC_VERSION="1.30"

LABEL maintainer="Alexis Lucattini"

# Add the requirements for the docker container
# This includes:
# * wget
# * bash
# * python3
# * aws cli
# * gzip
# * curl
# * uv (for running sequali)
# * sequali (the main tool we want to run)

ENV PYTHONUNBUFFERED=1
RUN \
    if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
      platform_url="aarch64";  \
    else \
      platform_url="x86_64"; \
    fi && \
    echo "Standard apt installations" 1>&2 && \
    apt update -yq && \
    apt upgrade -yq && \
    apt install -yq \
      wget \
      bash \
      python3 \
      pigz \
      curl \
      jq \
      unzip && \
    echo "Installing AWS CLI" 1>&2 && \
    wget \
      --quiet \
      --output-document "awscliv2.zip" \
      "https://awscli.amazonaws.com/awscli-exe-linux-${platform_url}.zip" && \
    unzip -q "awscliv2.zip" && \
    ./aws/install && \
    rm -r "awscliv2.zip" "aws" && \
    echo "Installing UV" 1>&2 && \
    curl -LsSf https://astral.sh/uv/install.sh | \
    XDG_CONFIG_HOME=/tmp UV_INSTALL_DIR=/usr/bin sh && \
    echo "Installing Python packages via uv" 1>&2 && \
    uv venv && \
    uv pip install \
      sequali=="${SEQUALI_VERSION}" \
      pyarrow=="${PYARROW_VERSION}" \
      pandas=="${PANDAS_VERSION}" \
      multiqc=="${MULTIQC_VERSION}"

# Copy the docker entrypoint to the docker container
COPY docker-entrypoint.sh docker-entrypoint.sh
COPY summarise_stats.py summarise_stats.py
COPY json_to_parquet.py json_to_parquet.py

# Make the docker entrypoint executable
RUN chmod +x "./docker-entrypoint.sh"
RUN chmod +x "./summarise_stats.py"

# Set the entrypoint as the docker entrypoint script
CMD [ "./docker-entrypoint.sh" ]
