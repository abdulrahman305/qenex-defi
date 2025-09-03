"""Real-time collaboration server for QENEX OS"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Set, List
from aiohttp import web
import aiohttp_cors
from aiohttp import WSMsgType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollaborationServer:
    """WebSocket-based real-time collaboration server"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}  # session_id -> session_info
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of session_ids
        self.websockets: Dict[str, web.WebSocketResponse] = {}  # session_id -> ws
        self.shared_state: Dict[str, Dict] = {}  # room_id -> shared state
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        session_id = str(uuid.uuid4())
        self.websockets[session_id] = ws
        
        # Send welcome message
        await ws.send_json({
            "type": "welcome",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.handle_message(session_id, data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            await self.disconnect_session(session_id)
            del self.websockets[session_id]
        
        return ws
    
    async def handle_message(self, session_id: str, message: Dict):
        """Handle incoming WebSocket messages"""
        msg_type = message.get("type")
        
        if msg_type == "join_room":
            await self.join_room(session_id, message)
        elif msg_type == "leave_room":
            await self.leave_room(session_id, message)
        elif msg_type == "broadcast":
            await self.broadcast_to_room(session_id, message)
        elif msg_type == "update_state":
            await self.update_shared_state(session_id, message)
        elif msg_type == "cursor_move":
            await self.broadcast_cursor(session_id, message)
        elif msg_type == "code_change":
            await self.handle_code_change(session_id, message)
        elif msg_type == "chat":
            await self.handle_chat(session_id, message)
        elif msg_type == "command":
            await self.handle_collaborative_command(session_id, message)
    
    async def join_room(self, session_id: str, message: Dict):
        """Join a collaboration room"""
        room_id = message.get("room_id")
        user_info = message.get("user_info", {})
        
        if not room_id:
            return
        
        # Create room if doesn't exist
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            self.shared_state[room_id] = {}
        
        # Add session to room
        self.rooms[room_id].add(session_id)
        self.sessions[session_id] = {
            "room_id": room_id,
            "user_info": user_info,
            "joined_at": datetime.now().isoformat()
        }
        
        # Notify room members
        await self.broadcast_to_room_members(room_id, {
            "type": "user_joined",
            "session_id": session_id,
            "user_info": user_info,
            "room_members": list(self.rooms[room_id])
        }, exclude=session_id)
        
        # Send current state to new member
        if session_id in self.websockets:
            await self.websockets[session_id].send_json({
                "type": "room_state",
                "room_id": room_id,
                "shared_state": self.shared_state[room_id],
                "members": [
                    self.sessions.get(sid, {}).get("user_info", {})
                    for sid in self.rooms[room_id]
                ]
            })
    
    async def leave_room(self, session_id: str, message: Dict):
        """Leave a collaboration room"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        room_id = session.get("room_id")
        if room_id and room_id in self.rooms:
            self.rooms[room_id].discard(session_id)
            
            # Notify room members
            await self.broadcast_to_room_members(room_id, {
                "type": "user_left",
                "session_id": session_id,
                "user_info": session.get("user_info", {})
            })
            
            # Clean up empty rooms
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                del self.shared_state[room_id]
        
        del self.sessions[session_id]
    
    async def broadcast_to_room(self, session_id: str, message: Dict):
        """Broadcast message to all room members"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        room_id = session.get("room_id")
        if room_id:
            await self.broadcast_to_room_members(room_id, {
                **message,
                "sender_id": session_id,
                "timestamp": datetime.now().isoformat()
            })
    
    async def broadcast_to_room_members(self, room_id: str, message: Dict, exclude: str = None):
        """Send message to all room members"""
        if room_id not in self.rooms:
            return
        
        tasks = []
        for member_id in self.rooms[room_id]:
            if member_id != exclude and member_id in self.websockets:
                tasks.append(self.websockets[member_id].send_json(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def update_shared_state(self, session_id: str, message: Dict):
        """Update shared state and sync with all members"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        room_id = session.get("room_id")
        if not room_id:
            return
        
        # Update state
        state_update = message.get("state", {})
        operation = message.get("operation", "merge")  # merge, replace, delete
        
        if operation == "merge":
            self.shared_state[room_id].update(state_update)
        elif operation == "replace":
            self.shared_state[room_id] = state_update
        elif operation == "delete":
            for key in state_update.get("keys", []):
                self.shared_state[room_id].pop(key, None)
        
        # Broadcast state change
        await self.broadcast_to_room_members(room_id, {
            "type": "state_updated",
            "state": self.shared_state[room_id],
            "operation": operation,
            "updated_by": session_id,
            "timestamp": datetime.now().isoformat()
        }, exclude=session_id)
    
    async def broadcast_cursor(self, session_id: str, message: Dict):
        """Broadcast cursor position to room members"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        room_id = session.get("room_id")
        if room_id:
            await self.broadcast_to_room_members(room_id, {
                "type": "cursor_update",
                "session_id": session_id,
                "position": message.get("position"),
                "user_info": session.get("user_info", {}),
                "timestamp": datetime.now().isoformat()
            }, exclude=session_id)
    
    async def handle_code_change(self, session_id: str, message: Dict):
        """Handle collaborative code editing"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        room_id = session.get("room_id")
        if room_id:
            # Apply Operational Transformation if needed
            change = message.get("change", {})
            
            # Broadcast change to other members
            await self.broadcast_to_room_members(room_id, {
                "type": "code_change",
                "session_id": session_id,
                "change": change,
                "file": message.get("file"),
                "timestamp": datetime.now().isoformat()
            }, exclude=session_id)
    
    async def handle_chat(self, session_id: str, message: Dict):
        """Handle chat messages"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        room_id = session.get("room_id")
        if room_id:
            await self.broadcast_to_room_members(room_id, {
                "type": "chat_message",
                "session_id": session_id,
                "user_info": session.get("user_info", {}),
                "message": message.get("text"),
                "timestamp": datetime.now().isoformat()
            })
    
    async def handle_collaborative_command(self, session_id: str, message: Dict):
        """Handle collaborative command execution"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        room_id = session.get("room_id")
        command = message.get("command")
        
        if room_id and command:
            # Execute command (mock implementation)
            result = f"Executed: {command}"
            
            # Broadcast result to all members
            await self.broadcast_to_room_members(room_id, {
                "type": "command_result",
                "session_id": session_id,
                "command": command,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
    
    async def disconnect_session(self, session_id: str):
        """Clean up disconnected session"""
        session = self.sessions.get(session_id)
        if session:
            await self.leave_room(session_id, {})

def create_app():
    """Create the collaboration server application"""
    app = web.Application()
    server = CollaborationServer()
    
    # Routes
    app.router.add_get('/ws', server.websocket_handler)
    
    # Health check
    async def health(request):
        return web.json_response({
            "status": "healthy",
            "active_sessions": len(server.sessions),
            "active_rooms": len(server.rooms)
        })
    
    app.router.add_get('/health', health)
    
    # CORS setup
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*"
        )
    })
    
    for route in list(app.router.routes()):
        cors.add(route)
    
    return app

if __name__ == "__main__":
    app = create_app()
    logger.info("Starting QENEX Collaboration Server on port 8080")
    web.run_app(app, host='0.0.0.0', port=8080)