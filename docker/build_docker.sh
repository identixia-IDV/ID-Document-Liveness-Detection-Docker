#!/usr/bin/env bash
# Build linux/amd64 image (runs on Linux / Windows / macOS Docker hosts).
set -euo pipefail
cd "$(dirname "$0")/.."
TAG="${1:-identixia/document-liveness:local}"

REPO="identixia-IDV/ID-Document-Liveness-Detection-Docker"
ASSET="documentliveness-linux.zip"
LIB_RELEASE_LATEST="https://github.com/${REPO}/releases/latest/download/${ASSET}"

need_runtime() {
  [[ ! -f lib/cpu/libDocLivenessSDK.so ]] \
    || [[ ! -f lib/cpu/libdcrliveness.so ]] \
    || [[ ! -f lib/cpu/document.xdb ]]
}

if need_runtime; then
  if [[ -f scripts/get_runtime.py ]]; then
    echo "lib/cpu incomplete — fetching GitHub Release runtime…"
    python3 scripts/get_runtime.py
  fi
fi

if need_runtime; then
  echo "ERROR: ./lib/cpu/ is incomplete."
  echo "Need: libDocLivenessSDK.so, libdcrliveness.so, document.xdb."
  echo "Download the Identixia Linux runtime into ./lib/cpu/:"
  echo "  python3 scripts/get_runtime.py"
  echo "  # $LIB_RELEASE_LATEST"
  exit 1
fi

docker build --platform linux/amd64 -f docker/Dockerfile -t "$TAG" .
echo "Built $TAG (linux/amd64)"
