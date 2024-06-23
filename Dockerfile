# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/

ARG PYTHON_VERSION=3.9.11
FROM python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/develop/develop-images/dockerfile_best-practices/#user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    seestar

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
# Disabled, until we have need for a requirements.txt file
#RUN --mount=type=cache,target=/root/.cache/pip \
#    --mount=type=bind,source=requirements.txt,target=requirements.txt \
#    python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.
USER seestar

# Copy the source code into the container.
COPY . .

#ENV SEESTAR_IP
#ENV SEESTAR_TARGET
#ENV SEESTAR_RA
#ENV SEESTAR_DEC
#ENV SEESTAR_LP_FILTER
#ENV SEESTAR_SESSION_TIME
#ENV SEESTAR_RA_PANEL_SZ
#ENV SEESTAR_DEC_PANEL_SZ
#ENV SEESTAR_RA_OFFSET_FACTOR
#ENV SEESTAR_DEC_OFFSET_FACTOR

# Run the application.
ENTRYPOINT [ "/bin/sh", "./seestar_entrypoint.sh" ]
