#!/bin/sh
# Build workspace helper: sync frontend source (no node_modules/.next) between the repo and a build dir.
# usage: sync_frontend.sh to-build|to-repo   (default build dir: /home/claude/fe)
BUILD=${BUILD_DIR:-/home/claude/fe}
REPO=$(cd "$(dirname "$0")/.." && pwd)/frontend
case "$1" in
  to-build) mkdir -p "$BUILD" && tar -C "$REPO" --exclude=node_modules --exclude=.next -cf - . | tar -C "$BUILD" -xf - ;;
  to-repo)  tar -C "$BUILD" --exclude=node_modules --exclude=.next --exclude=tsconfig.tsbuildinfo -cf - . | tar -C "$REPO" -xf - ;;
  *) echo "usage: $0 to-build|to-repo"; exit 1 ;;
esac
