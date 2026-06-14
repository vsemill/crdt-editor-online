from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import json

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.nodes = [] # Stores: {"value": "A", "position": "1.5", "userId": "user1"}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await websocket.send_text(json.dumps({
            "type": "sync", 
            "nodes": self.nodes,
            "origin": "server"
        }))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_state(self, origin_client_id: str):
        # The ultimate conflict resolution: Just sort the array mathematically!
        # It sorts by position string first, and uses userId as a tie-breaker.
        self.nodes.sort(key=lambda x: (x["position"], x["userId"]))
        
        message = json.dumps({"type": "sync", "nodes": self.nodes, "origin": origin_client_id})
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
                # The client already calculated the exact position. Just append and sort!
                manager.nodes.append({
                    "value": event["value"],
                    "position": event["position"], # We now accept the position string from JS
                    "userId": client_id
                })
                await manager.broadcast_state(client_id)
                
            elif event["type"] == "delete":
                # Delete by the specific position string, ignoring integer indices entirely
                manager.nodes = [n for n in manager.nodes if n["position"] != event["position"]]
                await manager.broadcast_state(client_id)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
