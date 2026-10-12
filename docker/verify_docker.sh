#!/usr/bin/env bash
# Rebuild and smoke-test the DocumentReader Docker image (needs docker + sudo).
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-14102}"

echo "==> Freeing host port ${PORT} (if a native API is still listening)"
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PORT}/tcp" 2>/dev/null || true
  sleep 1
fi

echo "==> Removing old container"
sudo docker rm -f identixia-document-reader 2>/dev/null || true

echo "==> Building (tags :local and :latest)"
sudo docker compose build
sudo docker tag identixia/document-reader:local identixia/document-reader:latest 2>/dev/null || true

echo "==> Starting"
sudo docker compose up -d
sleep 3

echo "==> Container status"
sudo docker ps --filter name=identixia-document-reader

echo "==> Recent logs"
sudo docker logs identixia-document-reader 2>&1 | tail -50

echo "==> Health"
curl -sf "http://127.0.0.1:${PORT}/api/health" | tee /dev/stderr
echo
curl -sf "http://127.0.0.1:${PORT}/api/machinecode" | tee /dev/stderr
echo
curl -sf "http://127.0.0.1:${PORT}/api/licenseStatus" | tee /dev/stderr
echo
echo "OK — API is up. Activate with a Docker-platform key via POST /api/activate if needed."
