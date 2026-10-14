# Enterprise System Deployment and Infrastructure Guide

## 1. Network Architecture and Ports
The architecture consists of three interconnected services:
- Frontend Single-Page Application (SPA): runs on port 5173 for local development and is served via static CDN in production.
- Backend FastAPI Service: listens on port 8000, exposed at `/api/v1`.
- Database Service: PostgreSQL 16 with pgvector extension listening on port 5432.

## 2. Connection Pooling Configuration
To prevent exhausting database memory on free-tier hosting:
- The database connection pool size is capped at 3 active connections.
- Connection timeout is set to 10 seconds with pre-ping validation enabled.
- Supabase session pooler on port 5432 must be used instead of direct IPv6 hosts.

## 3. FastEmbed Model Pre-caching
Embeddings utilize the local `BAAI/bge-small-en-v1.5` model (384 dimensions).
In deployment Dockerfiles, the model files must be downloaded during the container build step into the cache directory `/opt/render/project/.fastembed_cache` to eliminate cold-start latency.

## 4. Health Check Monitoring
The API provides two health probes:
- `/api/v1/health/live`: Liveness probe returning HTTP 200 `{"status": "ok"}`.
- `/api/v1/health/ready`: Readiness probe verifying database connectivity before routing user traffic.
Health monitoring systems should ping the readiness probe every 5 minutes.
