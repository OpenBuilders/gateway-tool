# Stage 1: Build the base image with the core package
FROM python:3.11.6-slim AS gateway-base

# Set environment variables
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/alembic.ini .
COPY backend/core/requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY backend/setup.py .
COPY backend/setup.cfg .

RUN pip install -e .

COPY backend/indexer ./indexer
COPY backend/core ./core

# Stage 2: Build the indexer image
FROM gateway-base AS indexer

COPY backend/indexer/requirements.txt requirements-indexer.txt
RUN pip install -r requirements-indexer.txt


# Stage 3: Build the community-manager image
FROM gateway-base AS community-manager

COPY backend/community_manager/requirements.txt requirements-community-manager.txt
RUN pip install -r requirements-community-manager.txt

COPY backend/community_manager ./community_manager

# Stage 4: FastAPI application
FROM gateway-base AS api

COPY backend/api/requirements.txt requirements-api.txt
RUN pip install -r requirements-api.txt

COPY backend/api ./api

# Stage 5: Scheduler image
FROM community-manager AS scheduler

COPY backend/scheduler ./scheduler
