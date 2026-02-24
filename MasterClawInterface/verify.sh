# Quick Test Script for MasterClaw Chat Interface
# This script verifies all components are properly set up

echo "🐾 MasterClaw Chat Interface - Quick Verification"
echo "=================================================="
echo ""

# Check Node.js version
echo "📦 Checking Node.js..."
node --version || { echo "❌ Node.js not installed"; exit 1; }
echo "✅ Node.js available"
echo ""

# Check if dependencies are installed
echo "📦 Checking Backend Dependencies..."
cd backend
if [ -d "node_modules" ]; then
    echo "✅ Backend dependencies installed"
else
    echo "⚠️  Backend dependencies missing - run: npm install"
fi
echo ""

# Check if .env exists
echo "🔧 Checking Environment Files..."
if [ -f ".env" ]; then
    echo "✅ Backend .env exists"
else
    echo "⚠️  Backend .env missing - copying from .env.example"
    cp .env.example .env
    echo "   Please edit .env with your settings"
fi
cd ..
echo ""

# Check frontend
echo "📦 Checking Frontend..."
cd frontend
if [ -d "node_modules" ]; then
    echo "✅ Frontend dependencies installed"
else
    echo "⚠️  Frontend dependencies missing - run: npm install"
fi
cd ..
echo ""

# Check SDK
echo "📦 Checking Agent SDK..."
cd sdk
if [ -f "agent-client.js" ]; then
    echo "✅ Agent SDK exists"
else
    echo "❌ Agent SDK missing"
fi
cd ..
echo ""

# Check Docker
echo "🐳 Checking Docker..."
if command -v docker &> /dev/null; then
    echo "✅ Docker available"
    if command -v docker-compose &> /dev/null; then
        echo "✅ Docker Compose available"
    else
        echo "⚠️  Docker Compose not found"
    fi
else
    echo "⚠️  Docker not installed (optional)"
fi
echo ""

echo "=================================================="
echo "✅ Verification Complete!"
echo ""
echo "🚀 Quick Start:"
echo ""
echo "1. Start with Docker (recommended):"
echo "   cd docker"
echo "   docker-compose up -d"
echo ""
echo "2. Or start manually:"
echo "   # Terminal 1 - Database"
echo "   docker run -d -p 5432:5432 -e POSTGRES_USER=masterclaw -e POSTGRES_PASSWORD=masterclaw_secret -e POSTGRES_DB=masterclaw_chat postgres:16-alpine"
echo ""
echo "   # Terminal 2 - Backend"
echo "   cd backend && npm run dev"
echo ""
echo "   # Terminal 3 - Frontend"
echo "   cd frontend && npm run dev"
echo ""
echo "📱 Access Points:"
echo "   - Chat UI:    http://localhost:5173 (or :3000 with Docker)"
echo "   - API:        http://localhost:3001"
echo "   - Health:     http://localhost:3001/health"
echo ""
echo "🧪 Test Agent SDK:"
echo "   cd sdk"
echo "   node test-client.js"
echo ""
