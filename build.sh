#!/usr/bin/env bash
# Rebuild frontend only (after UI changes)
set -e
echo "🏗️  Rebuilding frontend..."
cd frontend
npm run build
cd ..
echo "✅ Done — static/ updated. Restart main.py to serve."
