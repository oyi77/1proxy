#!/bin/bash
set -e

echo "🚀 Starting 1proxy Platform..."

echo ""
echo "📦 Starting Backend (FastAPI)..."
cd 1proxy-backend
PYTHONPATH=/Users/paijo/1proxy/1proxy-backend uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

echo ""
echo "⏳ Waiting for backend to be ready..."
sleep 5

echo ""
echo "🎨 Starting Frontend (Next.js)..."
cd 1proxy-frontend
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ 1proxy is running!"
echo ""
echo "🌐 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

wait
