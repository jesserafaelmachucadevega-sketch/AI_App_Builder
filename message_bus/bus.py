"""
Unified Message Bus

High-performance UDP/WebSocket listener for cross-agent communication.
Supports the Universal Agent Message Envelope schema.
"""

import asyncio
import json
import socket
import threading
import uuid
from datetime import datetime
from typing import Callable, Optional
from dataclasses import dataclass

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from schemas.message_envelope import (
    MessageEnvelope,
    MessageType,
    CoordinateVector,
    FileAttachment,
    Payload,
    validate_message
)


@dataclass
class BusConfig:
    """Configuration for the message bus."""
    udp_host: str = "0.0.0.0"
    udp_port: int = 5005
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8765
    buffer_size: int = 65536
    enable_udp: bool = True
    enable_websocket: bool = True
    broadcast_address: str = "<broadcast>"


class MessageBus:
    """
    Unified Message Bus for cross-agent communication.
    
    Supports:
    - UDP broadcast/multicast for low-latency local messaging
    - WebSocket for web-based clients and external integrations
    - Automatic JSON schema validation
    """
    
    def __init__(self, config: Optional[BusConfig] = None):
        self.config = config or BusConfig()
        self.handlers: dict[str, Callable] = {}
        self.coordinate_callbacks: list[Callable] = []
        self.file_modification_callbacks: list[Callable] = []
        self._running = False
        self._udp_socket: Optional[socket.socket] = None
        self._ws_server = None
        self._clients: set = set()
        
    def register_handler(self, message_type: str, handler: Callable[[MessageEnvelope], None]):
        """Register a handler for a specific message type."""
        self.handlers[message_type] = handler
        
    def on_coordinate_update(self, callback: Callable[[MessageEnvelope, CoordinateVector], None]):
        """Register callback for coordinate updates."""
        self.coordinate_callbacks.append(callback)
        
    def on_file_modification(self, callback: Callable[[MessageEnvelope, FileAttachment], None]):
        """Register callback for file modifications."""
        self.file_modification_callbacks.append(callback)
    
    def _process_message(self, data: dict, protocol: str) -> Optional[MessageEnvelope]:
        """Process and validate incoming message."""
        is_valid, errors = validate_message(data)
        
        if not is_valid:
            print(f"[Bus] Invalid message: {errors}")
            return None
            
        try:
            envelope = MessageEnvelope.from_dict(data)
            envelope.protocol = protocol
            return envelope
        except Exception as e:
            print(f"[Bus] Error parsing message: {e}")
            return None
    
    def _dispatch(self, envelope: MessageEnvelope):
        """Dispatch message to appropriate handlers."""
        # Call type-specific handler
        if envelope.message_type in self.handlers:
            self.handlers[envelope.message_type](envelope)
            
        # Call coordinate callbacks
        if envelope.message_type == MessageType.COORDINATE_UPDATE.value and envelope.payload.coordinates:
            for callback in self.coordinate_callbacks:
                callback(envelope, envelope.payload.coordinates)
                
        # Call file modification callbacks
        if envelope.message_type == MessageType.FILE_MODIFICATION.value:
            for attachment in envelope.payload.attachments:
                for callback in self.file_modification_callbacks:
                    callback(envelope, attachment)
    
    # ============ UDP Methods ============
    
    def start_udp(self):
        """Start UDP listener in a separate thread."""
        if not self.config.enable_udp:
            return
            
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            self._udp_socket.bind((self.config.udp_host, self.config.udp_port))
            self._udp_socket.settimeout(1.0)
            print(f"[Bus] UDP listening on {self.config.udp_host}:{self.config.udp_port}")
        except OSError as e:
            print(f"[Bus] Failed to bind UDP socket: {e}")
            return
            
        thread = threading.Thread(target=self._udp_listener, daemon=True)
        thread.start()
        
    def _udp_listener(self):
        """UDP listener loop."""
        while self._running:
            try:
                data, addr = self._udp_socket.recvfrom(self.config.buffer_size)
                message_data = json.loads(data.decode('utf-8'))
                envelope = self._process_message(message_data, "udp")
                
                if envelope:
                    print(f"[Bus] UDP message from {addr}: {envelope.message_type}")
                    self._dispatch(envelope)
                    
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                print(f"[Bus] Invalid UDP JSON: {e}")
            except Exception as e:
                if self._running:
                    print(f"[Bus] UDP error: {e}")
                    
    def send_udp(self, envelope: MessageEnvelope, broadcast: bool = True):
        """Send message via UDP."""
        if not self._udp_socket:
            print("[Bus] UDP socket not initialized")
            return
            
        try:
            data = envelope.to_json().encode('utf-8')
            target = (self.config.broadcast_address, self.config.udp_port) if broadcast else (self.config.udp_host, self.config.udp_port)
            self._udp_socket.sendto(data, target)
        except Exception as e:
            print(f"[Bus] UDP send error: {e}")
    
    # ============ WebSocket Methods ============
    
    async def _websocket_handler(self, websocket, path):
        """Handle WebSocket client connections."""
        self._clients.add(websocket)
        client_id = str(uuid.uuid4())[:8]
        print(f"[Bus] WebSocket client connected: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    message_data = json.loads(message)
                    envelope = self._process_message(message_data, "websocket")
                    
                    if envelope:
                        print(f"[Bus] WebSocket message from {client_id}: {envelope.message_type}")
                        self._dispatch(envelope)
                        
                        # Send acknowledgment
                        ack = MessageEnvelope(
                            message_id=str(uuid.uuid4()),
                            message_type=MessageType.AGENT_RESPONSE.value,
                            payload=Payload(action="acknowledged", data={"original_id": envelope.message_id}),
                            metadata={"client_id": client_id}
                        )
                        await websocket.send(ack.to_json())
                        
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            print(f"[Bus] WebSocket client disconnected: {client_id}")
    
    async def _ws_server_async(self):
        """Async WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            print("[Bus] websockets library not available")
            return
            
        self._ws_server = await websockets.serve(
            self._websocket_handler,
            self.config.websocket_host,
            self.config.websocket_port
        )
        print(f"[Bus] WebSocket server on ws://{self.config.websocket_host}:{self.config.websocket_port}")
        
    def start_websocket(self):
        """Start WebSocket server in async thread."""
        if not self.config.enable_websocket or not WEBSOCKETS_AVAILABLE:
            return
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ws_server_async())
        
        thread = threading.Thread(target=loop.run_forever, daemon=True)
        thread.start()
        
    async def broadcast_websocket(self, envelope: MessageEnvelope):
        """Broadcast message to all connected WebSocket clients."""
        if not self._clients:
            return
            
        message = envelope.to_json()
        await asyncio.gather(
            *[client.send(message) for client in self._clients],
            return_exceptions=True
        )
    
    # ============ Lifecycle Methods ============
    
    def start(self):
        """Start the message bus."""
        self._running = True
        self.start_udp()
        self.start_websocket()
        print(f"[Bus] Unified Message Bus started")
        
    def stop(self):
        """Stop the message bus."""
        self._running = False
        
        if self._udp_socket:
            self._udp_socket.close()
            
        if self._ws_server:
            self._ws_server.close()
            
        print("[Bus] Unified Message Bus stopped")
    
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# ============ Utility Functions ============

def create_coordinate_message(
    agent_id: str,
    agent_role: str,
    x: float,
    y: float,
    metadata: Optional[dict] = None
) -> MessageEnvelope:
    """Helper to create a coordinate update message."""
    return MessageEnvelope(
        message_id=str(uuid.uuid4()),
        source_agent={"id": agent_id, "role": agent_role},
        message_type=MessageType.COORDINATE_UPDATE.value,
        payload=Payload(
            action="update_coordinates",
            coordinates=CoordinateVector(
                x=x,
                y=y,
                agent_id=agent_id,
                metadata=metadata or {}
            )
        )
    )


def create_file_modification_message(
    agent_id: str,
    agent_role: str,
    filename: str,
    path: str,
    mime_type: str,
    size_bytes: int,
    checksum: Optional[str] = None
) -> MessageEnvelope:
    """Helper to create a file modification message."""
    return MessageEnvelope(
        message_id=str(uuid.uuid4()),
        source_agent={"id": agent_id, "role": agent_role},
        message_type=MessageType.FILE_MODIFICATION.value,
        payload=Payload(
            action="file_modified",
            resource=path,
            attachments=[FileAttachment(
                filename=filename,
                path=path,
                mime_type=mime_type,
                size_bytes=size_bytes,
                checksum=checksum
            )]
        )
    )
