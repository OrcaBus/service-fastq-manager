FROM alpine:3

ARG SEQUALI_VERSION="0.11.1"
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
RUN apk add --update --no-cache \
    wget \
    bash \
    python3 \
    aws-cli \
    pigz \
    curl && \
    curl -LsSf https://astral.sh/uv/install.sh | \
    XDG_CONFIG_HOME=/tmp UV_INSTALL_DIR=/usr/bin sh && \
    uvx pip install sequali=="${SEQUALI_VERSION}"

# Copy the docker entrypoint to the docker container
COPY docker-entrypoint.sh docker-entrypoint.sh
COPY summarise_stats.py summarise_stats.py

# Make the docker entrypoint executable
RUN chmod +x "./docker-entrypoint.sh"
RUN chmod +x "./summarise_stats.py"

# Set the entrypoint as the docker entrypoint script
CMD [ "./docker-entrypoint.sh" ]
