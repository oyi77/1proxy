#!/bin/bash
set -e

echo "🚀 Starting 1proxy Platform..."

# Copy .env from root to backend if it exists
if [ -f ".env" ]; then
    echo "📋 Copying .env to backend directory..."
    cp .env 1proxy-backend/.env
    echo "✅ .env synced to backend"
elif [ ! -f "1proxy-backend/.env" ]; then
    echo "⚠️  No .env file found. OAuth features will not work."
    echo "ℹ️  Copy .env.example to .env and configure your credentials"
fi

echo ""
echo "📦 Starting Backend (FastAPI)..."
cd 1proxy-backend
python run.py &
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
