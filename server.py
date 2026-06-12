from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json

app = FastAPI()

# --- 1. The CRDT Core Logic ---

def generate_position_between(left: str, right: str) -> str:
    """Generates a fractional index string between two existing strings."""
    left = left if left else "0"
    right = right if right else "9"
    
    base = 0
    new_pos = ""
    
    while base < len(left) or base < len(right):
        left_char = left[base] if base < len(left) else "0"
        right_char = right[base] if base < len(right) else "9"
        
        if left_char == right_char:
            new_pos += left_char
            base += 1
            continue
            
        left_val = ord(left_char)
        right_val = ord(right_char)
        
        if right_val - left_val > 1:
            mid_val = (left_val + right_val) // 2
            new_pos += chr(mid_val)
            return new_pos
        else:
            new_pos += left_char
            left += "0"
            base += 1
            
    return new_pos + "5"

class CRDTDocument:
    def __init__(self):
        self.nodes = [] # Stores dictionaries: {"value": "A", "position": "1.5", "userId": "user1"}
        
    def insert(self, index: int, value: str, user_id: str):
        # Find neighbors based on visual index
        left_pos = self.nodes[index - 1]["position"] if index > 0 else None
        right_pos = self.nodes[index]["position"] if index < len(self.nodes) else None
        
        # Calculate mathematical position
        new_pos = generate_position_between(left_pos, right_pos)
        
        new_node = {"value": value, "position": new_pos, "userId": user_id}
        self.nodes.insert(index, new_node)
        return new_node

    def delete(self, index: int):
        if 0 <= index < len(self.nodes):
            return self.nodes.pop(index)
        elif event["type"] == "delete":
                # Get the length of the highlighted text (default to 1 if not provided)
                delete_length = event.get("length", 1)
                
                # Pop the character at the same index multiple times
                for _ in range(delete_length):
                    manager.document.delete(event["index"])
                    
                await manager.broadcast_state(client_id)
        return None

# --- 2. The WebSocket Manager ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.document = CRDTDocument()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Tag initial sync as coming from the "server"
        await websocket.send_text(json.dumps({
            "type": "sync", 
            "content": "".join([n["value"] for n in self.document.nodes]),
            "origin": "server"
        }))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    # FIX: Add origin_client_id parameter
    async def broadcast_state(self, origin_client_id: str):
        full_text = "".join([n["value"] for n in self.document.nodes])
        # FIX: Include the origin in the JSON message
        message = json.dumps({"type": "sync", "content": full_text, "origin": origin_client_id})
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            event = json.loads(data)
            
            if event["type"] == "insert":
                manager.document.insert(event["index"], event["value"], client_id)
                # FIX: Pass the client_id to the broadcast
                await manager.broadcast_state(client_id)
                
            elif event["type"] == "delete":
                manager.document.delete(event["index"])
                # FIX: Pass the client_id to the broadcast
                await manager.broadcast_state(client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
