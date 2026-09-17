FROM public.ecr.aws/ubuntu/ubuntu:noble

# Note means we must use ubuntu as base image for now
LABEL maintainer="Alexis Lucattini"

# For multiarch images
ARG TARGETPLATFORM

# Set build arguments for versions
ARG SAMTOOLS_VERSION="1.22.1"
ARG MINIMAP2_VERSION="2.30"
ARG PICARD_VERSION="3.3.0"
ARG PYARROW_VERSION="20.0.0"
ARG PANDAS_VERSION="2.3.3"
ARG MULTIQC_VERSION="1.31"

ENV PYTHONUNBUFFERED=1

# Where the Picard jar lives + a wrapper on the PATH
ENV PICARD_JAR="/opt/picard/picard.jar"

# Install dependencies, samtools, minimap2, aws cli, a JRE, R and Picard.
# R (r-base-core) is required by Picard CollectInsertSizeMetrics, which shells
# out to Rscript to render the insert-size histogram PDF.
# The alignment toolchain (minimap2 / samtools / aws cli + build deps) mirrors
# app/ecs/tiny_alignment/Dockerfile. bedops / bedtools / somalier / nim / slivar
# are intentionally omitted - they are not required for insert-size collection.
RUN \
    if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
      platform_url="aarch64";  \
    else \
      platform_url="x86_64"; \
    fi && \
    echo "Standard APT" 1>&2 && \
    apt update -yq && \
    apt upgrade -yq && \
    # Basics along with htslib/samtools deps and a headless JRE (for Picard) \
    apt install -yq \
      build-essential \
      libz-dev \
      wget \
      curl \
      pigz \
      unzip \
      jq \
      python3 \
      git \
      zlib1g-dev \
      libbz2-dev \
      liblzma-dev \
      xz-utils \
      libssl-dev \
      libncurses5-dev \
      libcurl4-openssl-dev \
      procps \
      libopenblas-dev \
      libgomp1 \
      default-jre-headless \
      r-base-core && \
    # Download + Install samtools \
    wget \
      --quiet \
      --output-document "samtools-${SAMTOOLS_VERSION}.tar.bz2" \
      "https://github.com/samtools/samtools/releases/download/${SAMTOOLS_VERSION}/samtools-${SAMTOOLS_VERSION}.tar.bz2" && \
    tar -xf "samtools-${SAMTOOLS_VERSION}.tar.bz2" && \
    ( \
      cd "samtools-${SAMTOOLS_VERSION}" && \
      ./configure \
        --enable-plugins \
        --prefix=/usr && \
      make all all-htslib && \
      make install install-htslib \
    ) && \
    rm -rf \
      "samtools-${SAMTOOLS_VERSION}" \
      "samtools-${SAMTOOLS_VERSION}.tar.bz2" && \
    # Install AWS CLI \
    wget \
      --quiet \
      --output-document "awscliv2.zip" \
      "https://awscli.amazonaws.com/awscli-exe-linux-${platform_url}.zip" && \
    unzip -q "awscliv2.zip" && \
    ./aws/install \
      --install-dir /usr/aws-cli \
      --bin-dir /usr/bin && \
    rm -rf "awscliv2.zip" "aws/" && \
    # Install minimap2 (built from source for multiarch support) \
    wget --quiet \
      --output-document - \
      "https://github.com/lh3/minimap2/releases/download/v${MINIMAP2_VERSION}/minimap2-${MINIMAP2_VERSION}.tar.bz2" | \
    tar \
      --bzip2 \
      --extract \
      --file - && \
    ( \
      cd "minimap2-${MINIMAP2_VERSION}" && \
      if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
        make \
          arm_neon=1 aarch64=1; \
      else \
        make; \
      fi && \
      chmod +x minimap2 && \
      mv minimap2 /usr/bin/ \
    ) && \
    rm -rf "minimap2-${MINIMAP2_VERSION}" && \
    # Install Picard (architecture-independent jar) + a wrapper on the PATH \
    mkdir -p /opt/picard && \
    wget \
      --quiet \
      --output-document "${PICARD_JAR}" \
      "https://github.com/broadinstitute/picard/releases/download/${PICARD_VERSION}/picard.jar" && \
    printf '#!/usr/bin/env bash\nexec java -jar "%s" "$@"\n' "${PICARD_JAR}" > /usr/bin/picard && \
    chmod +x /usr/bin/picard

# Install UV + Python tooling (multiqc + parquet conversion), mirroring get_sequali_stats
RUN \
    echo "Installing UV" 1>&2 && \
    curl -LsSf https://astral.sh/uv/install.sh | \
    XDG_CONFIG_HOME=/tmp UV_INSTALL_DIR=/usr/bin sh && \
    echo "Installing Python packages via uv" 1>&2 && \
    uv venv && \
    uv pip install \
      pyarrow=="${PYARROW_VERSION}" \
      pandas=="${PANDAS_VERSION}" \
      multiqc=="${MULTIQC_VERSION}"

# Copy the docker entrypoint and metrics-to-parquet converter into the container
COPY docker-entrypoint.sh docker-entrypoint.sh
COPY metrics_to_parquet.py metrics_to_parquet.py

# Make the docker entrypoint executable
RUN chmod +x "./docker-entrypoint.sh"

# Set the entrypoint as the docker entrypoint script
CMD [ "./docker-entrypoint.sh" ]
