FROM public.ecr.aws/lambda/python:3.12

ARG TARGETPLATFORM

ARG MULTIQC_VERSION=1.30.0
ARG PANDAS_VERSION=2.3.1

ARG APP_ROOT=.

RUN \
  # Install dependencies
  dnf update -y && \
  dnf install -y \
    tar \
    gzip \
    wget && \
  # Install the required Python packages using uv
  pip install --break-system-packages \
    multiqc=="${MULTIQC_VERSION}" \
    pandas=="${PANDAS_VERSION}"

# Copy the lambda contents
COPY ${APP_ROOT}/run_multiqc.py ./

CMD ["run_multiqc.handler"]
