# Dashboard Backend

## Running locally

```bash
uv run python main.py
```

## Docker

```bash
# Build image
DOCKER_BUILDKIT=1 docker build -t polymarket-backend .

# Run container
docker run --rm -p 8000:8000 \
  --env-file .env.local \
  polymarket-backend
```
