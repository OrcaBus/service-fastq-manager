FROM ghcr.io/umccr/orad:2.7.0


ARG SAMTOOLS_VERSION=""
ARG MINIMAP2_VERSION=""
ARG BEDTOOLS_VERSION=""


# Install debian basics
RUN \
    if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
      platform_url="aarch64";  \
    else \
      platform_url="x86_64"; \
    fi && \
    echo "Standard APT" 1>&2 && \
    apt update -yq && \
    apt upgrade -yq && \
    apt install -yq \
      wget \
      curl \
      jq \
      git \
      gzip \
      unzip \
      pigz \
      libz-dev \
      build-essential && \
