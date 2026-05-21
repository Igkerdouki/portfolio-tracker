#!/bin/bash

# Portfolio Tracker - Start Script
cd "$(dirname "$0")"

echo "Starting Portfolio Tracker..."

# Start backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
sleep 2

# Start frontend
cd frontend
/opt/homebrew/bin/npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to be ready
sleep 3

# Open browser
open http://localhost:5173

echo ""
echo "Portfolio Tracker is running!"
echo "  - Frontend: http://localhost:5173"
echo "  - Backend:  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
