FROM public.ecr.aws/ubuntu/ubuntu:noble

# Note means we must use ubuntu as base image for now
LABEL maintainer="Alexis Lucattini"

# For multiarch images
ARG TARGETPLATFORM

# Set build arguments for versions
ARG BEDOPS_VERSION="2.4.42"
ARG SAMTOOLS_VERSION="1.22.1"
ARG MINIMAP2_VERSION="2.30"
ARG BEDTOOLS_VERSION="2.31.1"
ARG SOMALIER_VERSION="0.3.1"
ARG NIM_VERSION="1.6.10"

# Install dependencies, samtools and somalier
RUN \
    if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
      platform_url="aarch64";  \
    else \
      platform_url="x86_64"; \
    fi && \
    echo "Standard APT" 1>&2 && \
    apt update -yq && \
    apt upgrade -yq && \
    # Basics along with htslib/samtools deps \
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
      liblzma-dev \
      procps \
      libopenblas-dev \
      libgomp1 && \
    # Download + Install bedops \
    wget \
      --quiet \
      --output-document "-" \
      "https://github.com/bedops/bedops/archive/refs/tags/v${BEDOPS_VERSION}.tar.gz" | \
    tar -xzf - && \
    ( \
      cd "bedops-${BEDOPS_VERSION}" && \
      make all && \
      make install && \
      cp bin/* /usr/bin/ \
    ) && \
    rm -rf "bedops-${BEDOPS_VERSION}" && \
    # Download + Install bedtools \
    wget \
      --quiet \
      --output-document "-" \
      "https://github.com/arq5x/bedtools2/releases/download/v${BEDTOOLS_VERSION}/bedtools-${BEDTOOLS_VERSION}.tar.gz" | \
    tar -xzf - && \
    ( \
      cd "bedtools2" && \
      make && \
      prefix=/usr \
      make install \
    ) && \
    rm -rf "bedtools2" && \
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
    ./aws/install \
      --install-dir /usr/aws-cli \
      --bin-dir /usr/bin && \
    rm -rf "awscliv2.zip" "aws/" \
        build-essential && \
    # Install minimap2 \
    wget --quiet \
      --output-document - \
      "https://github.com/lh3/minimap2/releases/download/v${MINIMAP2_VERSION}/minimap2-${MINIMAP2_VERSION}.tar.bz2" | \
    tar \
      --bzip2 \
      --extract \
      --file - && \
    # Build minimap2 \
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
    # Create /opt directory for miscell installations  \
    mkdir -p /opt && \
    # Install nim (required by somalier) \
    ( \
      cd /opt && \
      git clone \
      --branch "v${NIM_VERSION}" \
      --depth 1 \
      "https://github.com/nim-lang/nim" && \
      ( \
        cd nim && \
        bash build_all.sh \
      ) && \
      ln -s /opt/nim/bin/nim /usr/bin/nim && \
      ln -s /opt/nim/bin/nimble /usr/bin/nimble \
    ) && \
    # Install slivar - somalier depends on this package for some functionality \
    ( \
      cd /opt && \
      git clone \
        --depth 1 \
        https://github.com/brentp/slivar.git && \
      ( \
        cd slivar && \
        if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
          find . -type f -name "*.nim" -exec sed -i '/-mpopcnt/d' {} \; && \
          find . -type f -name "nimble" -exec sed -i '/-mpopcnt/d' {} \; && \
          (find . -type f -name "*.cfg" -exec sed -i '/-mpopcnt/d' {} \; || true); \
        fi && \
        nimble install -y \
      ) \
    ) && \
    # Install somalier \
    ( \
      cd /opt && \
      git clone \
        --depth 1 \
        --branch "v${SOMALIER_VERSION}" \
        "https://github.com/brentp/somalier.git" && \
      ( \
        cd somalier && \
        # Fix for arm64 architecture \
        if [ "${TARGETPLATFORM#linux/}" = "arm64" ]; then \
          find . -type f -name "*.nim" -exec sed -i '/-mpopcnt/d' {} \; && \
          find . -type f -name "nimble" -exec sed -i '/-mpopcnt/d' {} \; && \
          find . -type f -name "*.cfg" -exec sed -i '/-mpopcnt/d' {} \; && \
          # Remove slivar dependency from somalier.nimble because for arm64 we have already installed it. \
          (sed -i '/slivar/d' /opt/somalier/somalier.nimble || true); \
        fi && \
        # Install somalier \
        nimble install -d -y && \
        nim c \
          -d:danger \
          -d:nsb_static \
          -d:release \
          -d:nimDebugDlOpen \
          -d:openmp \
          -d:blas=openblas \
          -d:lapack=openblas \
          -o:/usr/bin/somalier \
          "src/somalier" \
      ) \
    )

# Copy the docker entrypoint to the docker container
COPY docker-entrypoint.sh docker-entrypoint.sh

# Make the docker entrypoint executable
RUN chmod +x "./docker-entrypoint.sh"

# Set the entrypoint as the docker entrypoint script
CMD [ "./docker-entrypoint.sh" ]
