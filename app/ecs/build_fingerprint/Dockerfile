FROM ubuntu:noble

# Note means we must use ubuntu as base image for now
LABEL maintainer="Alexis Lucattini"

# Install dependencies and somalier
ARG HTSLIB_VERSION="1.22"
ARG SAMTOOLS_VERSION="1.22.1"
ARG BEDTOOLS_VERSION="2.31.0"
ARG SOMALIER_VERSION="0.3.1"
ARG TARGETPLATFORM
ARG SOMALIER_STATIC_BINARY="https://github.com/brentp/somalier/releases/download/v${SOMALIER_VERSION}/somalier"

# Install dependencies, samtools and somalier
RUN \
  if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
    platform_url="aarch64";  \
  else \
    platform_url="x86_64"; \
  fi && \
  apt update -y -q && \
  apt upgrade -y -q && \
  # Basics along with htslib/samtools deps \
  apt install -yq \
    build-essential \
    libz-dev \
    wget \
    pigz \
    unzip \
    jq \
    zlib1g-dev \
    libbz2-dev \
    liblzma-dev \
    xz-utils \
    libssl-dev \
    libncurses5-dev \
    libcurl4-openssl-dev && \
  # Download + Install bedtools \
  wget \
    --quiet \
    --output-document "/usr/bin/bedtools" \
    "https://github.com/arq5x/bedtools2/releases/download/v${BEDTOOLS_VERSION}/bedtools.static" && \
  chmod +x "/usr/bin/bedtools" && \
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
  # Install AWS \
  wget \
    --quiet \
    --output-document "awscliv2.zip" \
    "https://awscli.amazonaws.com/awscli-exe-linux-${platform_url}.zip" && \
  unzip -q "awscliv2.zip" && \
  ./aws/install && \
  rm -rf "awscliv2.zip" "aws/" \
  # Install somalier \
  wget \
    --quiet \
    --output-document "/usr/bin/somalier" \
    "https://github.com/brentp/somalier/releases/download/v${SOMALIER_VERSION}/somalier" && \
  chmod +x "/usr/bin/somalier"

# Copy the docker entrypoint to the docker container
COPY docker-entrypoint.sh docker-entrypoint.sh

# Make the docker entrypoint executable
RUN chmod +x "./docker-entrypoint.sh"

# Set the entrypoint as the docker entrypoint script
CMD [ "./docker-entrypoint.sh" ]
