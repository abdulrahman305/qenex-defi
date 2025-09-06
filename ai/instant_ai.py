#!/usr/bin/env python3
"""
QENEX Instant AI - Operational in seconds
"""

import ollama
import asyncio
import json
from fastapi import FastAPI
from typing import Dict, Any
import multiprocessing as mp

app = FastAPI(title="QENEX Instant AI")
client = ollama.Client()

class InstantAI:
    def __init__(self):
        self.model = "mistral:latest"
        self.ready = False
        self.responses = 0
        self.total_time = 0
        
    async def initialize(self):
        """Quick initialization"""
        try:
            # Test model
            response = client.generate(model=self.model, prompt="test")
            self.ready = True
            return True
        except:
            self.model = "phi:latest"  # Fallback to smaller model
            try:
                response = client.generate(model=self.model, prompt="test")
                self.ready = True
            except:
                self.ready = False
        return self.ready
    
    async def instant_response(self, prompt: str) -> str:
        """Get instant AI response"""
        if not self.ready:
            await self.initialize()
        
        start = asyncio.get_event_loop().time()
        response = client.generate(
            model=self.model,
            prompt=prompt,
            options={"num_predict": 100}  # Short for speed
        )
        
        elapsed = asyncio.get_event_loop().time() - start
        self.responses += 1
        self.total_time += elapsed
        
        return response['response']
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance stats"""
        avg_time = self.total_time / self.responses if self.responses > 0 else 0
        return {
            "ready": self.ready,
            "model": self.model,
            "responses": self.responses,
            "avg_response_time": avg_time,
            "responses_per_second": 1/avg_time if avg_time > 0 else 0
        }

# Global AI instance
ai = InstantAI()

@app.on_event("startup")
async def startup():
    await ai.initialize()

@app.get("/")
async def root():
    return {
        "status": "operational",
        "ai_ready": ai.ready,
        "stats": ai.get_stats()
    }

@app.post("/ai")
async def get_ai_response(prompt: str):
    response = await ai.instant_response(prompt)
    return {
        "prompt": prompt,
        "response": response,
        "stats": ai.get_stats()
    }

@app.get("/health")
async def health():
    return {"healthy": ai.ready}

if __name__ == "__main__":
    import uvicorn
    
    # Initialize AI
    asyncio.run(ai.initialize())
    
    # Run server with maximum workers
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7777,
        workers=mp.cpu_count(),
        log_level="error"  # Minimal logging for speed
    )
