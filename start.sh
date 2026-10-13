#!/usr/bin/env bash
# CureCompass — One-command start script
# Usage: ./start.sh
set -e

echo ""
echo "🔧 CureCompass — Intelligent Incident Remediation Platform"
echo "══════════════════════════════════════════════════"
echo ""

# 1. Check .env
if [ ! -f .env ]; then
  echo "⚠️  No .env found. Copying .env.example → .env"
  cp .env.example .env
  echo "   Edit .env with your Dynatrace + Anthropic credentials, then re-run."
  echo ""
fi

# 2. Python deps
echo "📦 Installing Python dependencies..."
python -m pip install -r requirements.txt -q

# 3. Build frontend if not already built
if [ ! -d "static" ]; then
  echo ""
  echo "🏗️  Building React frontend..."
  cd frontend
  npm install --silent
  npm run build
  cd ..
  echo "   ✅ Frontend built → static/"
fi

echo ""
PORT="${PORT:-8000}"
echo "🚀 Starting CureCompass..."
echo "   Visit: http://localhost:${PORT}"
echo "   API Docs: http://localhost:${PORT}/docs"
echo ""

python main.py
