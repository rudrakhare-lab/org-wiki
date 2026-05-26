#!/bin/bash
# Start the Conwo backend + Angular frontend for local development.
#
# Usage:
#   ./start.sh
#
# Prerequisites:
#   1. Install backend deps: venv/bin/pip install -r requirements-backend.txt
#   2. Install frontend deps: cd frontend && npm install
#   3. Set your admin token in config/allowed_users.toml:
#      token = "$(python -c "import hashlib; print(hashlib.sha256(b'your@email.com').hexdigest()[:32])")"

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🧠 Starting Conwo..."

# Backend
echo "  → Starting FastAPI backend on http://localhost:8000"
PYTHONPATH="$SCRIPT_DIR/scripts:$SCRIPT_DIR" \
  "$SCRIPT_DIR/venv/bin/uvicorn" backend.api:app \
  --host 0.0.0.0 --port 8000 --reload \
  --app-dir "$SCRIPT_DIR" &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Frontend — disable analytics prompt first so it doesn't block in background
echo "  → Starting Angular dev server on http://localhost:4200"
cd "$SCRIPT_DIR/frontend" && npx ng analytics disable --global 2>/dev/null || true
npx ng serve --port 4200 --no-open &
FRONTEND_PID=$!

echo ""
echo "✅ Conwo running:"
echo "   Frontend: http://localhost:4200"
echo "   Backend:  http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait for either process to exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait $BACKEND_PID $FRONTEND_PID
