FROM ubuntu:noble

# Note - gcc compiler error in alpine
# means we must use ubuntu as base image for now

LABEL maintainer="Alexis Lucattini"

ARG NTSM_VERSION="1.2.1"
ARG TARGETPLATFORM
ARG NTSM_DOWNLOAD_URL="https://github.com/JustinChu/ntsm/releases/download/${NTSM_VERSION}/ntsm-${NTSM_VERSION}.tar.gz"
ARG NTSM_FASTA_DOWNLOAD_URL="https://github.com/JustinChu/ntsm/raw/refs/heads/main/data/human_sites_n10.fa"
ARG NTSM_OUTPUT_FASTA_PATH="/opt/ntsm/human_sites_n10.fa"

RUN \
  if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
    platform_url="aarch64";  \
  else \
    platform_url="x86_64"; \
  fi && \
  apt update -y -q && \
  apt upgrade -y -q && \
  apt install -yq \
    build-essential \
    libz-dev \
    wget \
    pigz \
    unzip && \
  ( \
    wget \
      --quiet \
      --output-document "awscliv2.zip" \
      "https://awscli.amazonaws.com/awscli-exe-linux-${platform_url}.zip" && \
    unzip -q "awscliv2.zip" && \
    ./aws/install && \
    rm -rf "awscliv2.zip" "aws/" \
  ) && \
  ( \
    wget --quiet \
      --output-document "$(basename "${NTSM_DOWNLOAD_URL}")" \
      "${NTSM_DOWNLOAD_URL}" && \
    tar -xzf "$(basename "${NTSM_DOWNLOAD_URL}")" && \
    cd "$(basename "${NTSM_DOWNLOAD_URL}" .tar.gz)" && \
    ./configure && \
    make && \
    make install \
  )

RUN mkdir -p "$(dirname "${NTSM_OUTPUT_FASTA_PATH}")" && \
    wget \
       --quiet \
       --output-document "${NTSM_OUTPUT_FASTA_PATH}" \
      "${NTSM_FASTA_DOWNLOAD_URL}"

ENV NTSM_FASTA_PATH="${NTSM_OUTPUT_FASTA_PATH}"

# Copy the docker entrypoint to the docker container
COPY docker-entrypoint.sh docker-entrypoint.sh

# Make the docker entrypoint executable
RUN chmod +x "./docker-entrypoint.sh"

# Set the entrypoint as the docker entrypoint script
CMD [ "./docker-entrypoint.sh" ]
