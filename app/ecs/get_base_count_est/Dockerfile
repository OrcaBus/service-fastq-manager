FROM alpine:3

LABEL maintainer="Alexis Lucattini"

# Add the requirements for the docker container
# This includes:
# * wget
# * bash
# * python3
# * aws cli
# * gzip

ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache \
    wget \
    bash \
    python3 \
    aws-cli \
    gzip


# Copy the docker entrypoint to the docker container
COPY docker-entrypoint.sh docker-entrypoint.sh

# Make the docker entrypoint executable
RUN chmod +x "./docker-entrypoint.sh"

# Set the entrypoint as the docker entrypoint script
CMD [ "./docker-entrypoint.sh" ]
