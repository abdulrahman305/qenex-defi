#!/bin/bash

echo "🚀 Launching QENEX AI..."

# Start Ollama in background
ollama serve > /dev/null 2>&1 &
OLLAMA_PID=$!

# Give Ollama 2 seconds to start
sleep 2

# Launch instant AI
python3 /opt/qenex-os/ai/instant_ai.py &
AI_PID=$!

# Launch unlimited goal optimizer
python3 /opt/qenex-os/ai/unlimited_goal_optimizer.py &
OPTIMIZER_PID=$!

echo "✅ QENEX AI OPERATIONAL"
echo ""
echo "📍 Access Points:"
echo "  • Instant AI: http://localhost:7777"
echo "  • API Docs: http://localhost:7777/docs"
echo ""
echo "📊 Process IDs:"
echo "  • Ollama: $OLLAMA_PID"
echo "  • AI Server: $AI_PID"
echo "  • Goal Optimizer: $OPTIMIZER_PID"
echo ""
echo "⚡ AI is achieving unlimited improvement!"

# Keep running
wait
