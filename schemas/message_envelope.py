"""
Universal Agent Message Envelope Schema

This module defines the JSON schema for cross-agent communication.
All messages between agents must conform to this structure.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import json


class MessageType(Enum):
    """Types of messages that can be sent through the bus."""
    COORDINATE_UPDATE = "coordinate_update"
    FILE_MODIFICATION = "file_modification"
    STATE_CHANGE = "state_change"
    AGENT_REQUEST = "agent_request"
    AGENT_RESPONSE = "agent_response"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class AgentRole(Enum):
    """Roles of agents in the system."""
    COORDINATOR = "coordinator"
    CODER = "coder"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"
    MONITOR = "monitor"


class Protocol(Enum):
    """Network protocols supported by the message bus."""
    UDP = "udp"
    WEBSOCKET = "websocket"


@dataclass
class FileAttachment:
    """Represents a file attachment in a message."""
    filename: str
    path: str
    mime_type: str
    size_bytes: int
    checksum: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class CoordinateVector:
    """2D coordinate vector for agent positioning."""
    x: float
    y: float
    agent_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)


@dataclass
class Payload:
    """Core payload of the message envelope."""
    action: str
    resource: Optional[str] = None
    data: Optional[dict] = None
    coordinates: Optional[CoordinateVector] = None
    attachments: list[FileAttachment] = field(default_factory=list)


@dataclass
class MessageEnvelope:
    """
    Universal Agent Message Envelope
    
    All cross-agent communication uses this JSON structure:
    {
        "envelope_version": "1.0",
        "message_id": "uuid",
        "timestamp": "ISO8601",
        "source_agent": {"id": "...", "role": "..."},
        "target_agent": {"id": "...", "role": "..."},
        "message_type": "...",
        "protocol": "...",
        "payload": {...},
        "routing": {...},
        "metadata": {...}
    }
    """
    envelope_version: str = "1.0"
    message_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_agent: dict = field(default_factory=dict)
    target_agent: dict = field(default_factory=dict)
    message_type: str = MessageType.AGENT_REQUEST.value
    protocol: str = Protocol.UDP.value
    payload: Payload = field(default_factory=Payload)
    routing: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize the envelope to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> dict:
        """Convert envelope to dictionary."""
        def _serialize(obj):
            if isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, '__dataclass_fields__'):
                # Handle dataclasses
                return {f: _serialize(getattr(obj, f)) for f in obj.__dataclass_fields__}
            return obj
        
        result = {}
        for key, value in self.__dict__.items():
            result[key] = _serialize(value)
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'MessageEnvelope':
        """Create envelope from dictionary (non-mutating)."""
        data = dict(data)  # defensive copy
        
        # Reconstruct payload dataclass from raw dict if present
        if 'payload' in data and isinstance(data['payload'], dict):
            payload_raw = dict(data['payload'])  # defensive copy
            if 'coordinates' in payload_raw and isinstance(payload_raw['coordinates'], dict):
                coord_data = payload_raw['coordinates']
                payload_raw['coordinates'] = CoordinateVector(**coord_data) if coord_data else None
            # Reconstruct attachments as FileAttachment objects
            if 'attachments' in payload_raw and isinstance(payload_raw['attachments'], list):
                payload_raw['attachments'] = [FileAttachment(**a) if isinstance(a, dict) else a for a in payload_raw['attachments']]
            data['payload'] = Payload(**payload_raw)
        
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'MessageEnvelope':
        """Create envelope from JSON string."""
        return cls.from_dict(json.loads(json_str))


# JSON Schema (for validation)
UNIVERSAL_MESSAGE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Universal Agent Message Envelope",
    "type": "object",
    "required": ["envelope_version", "message_id", "timestamp", "source_agent", "message_type", "payload"],
    "properties": {
        "envelope_version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+$"
        },
        "message_id": {
            "type": "string",
            "format": "uuid"
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "source_agent": {
            "type": "object",
            "required": ["id", "role"],
            "properties": {
                "id": {"type": "string"},
                "role": {"type": "string", "enum": [r.value for r in AgentRole]},
                "metadata": {"type": "object"}
            }
        },
        "target_agent": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "role": {"type": "string", "enum": [r.value for r in AgentRole]},
                "metadata": {"type": "object"}
            }
        },
        "message_type": {
            "type": "string",
            "enum": [mt.value for mt in MessageType]
        },
        "protocol": {
            "type": "string",
            "enum": [p.value for p in Protocol]
        },
        "payload": {
            "type": "object",
            "required": ["action"],
            "properties": {
                "action": {"type": "string"},
                "resource": {"type": "string"},
                "data": {"type": "object"},
                "coordinates": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "agent_id": {"type": "string"},
                        "timestamp": {"type": "string"}
                    }
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["filename", "path", "mime_type", "size_bytes"],
                        "properties": {
                            "filename": {"type": "string"},
                            "path": {"type": "string"},
                            "mime_type": {"type": "string"},
                            "size_bytes": {"type": "integer"},
                            "checksum": {"type": "string"}
                        }
                    }
                }
            }
        },
        "routing": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["low", "normal", "high", "critical"]},
                "ttl": {"type": "integer"},
                "hop_limit": {"type": "integer"}
            }
        },
        "metadata": {
            "type": "object"
        }
    }
}


def validate_message(data: dict) -> tuple[bool, list[str]]:
    """Validate a message against the full schema. Returns (is_valid, errors).
    
    Checks required fields, types, nested structures, and enum values
    at every level of the message envelope.
    """
    errors = []
    
    # --- Top-level required fields ---
    for field in UNIVERSAL_MESSAGE_SCHEMA["required"]:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors
    
    schema = UNIVERSAL_MESSAGE_SCHEMA["properties"]

    # --- envelope_version ---
    pattern = schema["envelope_version"].get("pattern")
    if pattern:
        import re
        v = data.get("envelope_version", "")
        if not re.match(pattern, v):
            errors.append(f"envelope_version must match {pattern}, got '{v}'")

    # --- message_id: non-empty uuid-like ---
    mid = data.get("message_id", "")
    if not mid:
        errors.append("message_id must not be empty")

    # --- timestamp: non-empty ---
    ts = data.get("timestamp", "")
    if not ts:
        errors.append("timestamp must not be empty")

    # --- source_agent: required id + role ---
    src_schema = schema["source_agent"]
    source = data.get("source_agent", {})
    src_required = src_schema.get("required", [])
    for field in src_required:
        if field not in source:
            errors.append(f"source_agent missing '{field}'")
    # Validate role enum
    role_enum = src_schema.get("properties", {}).get("role", {}).get("enum", [])
    if source.get("role") not in role_enum:
        errors.append(f"source_agent.role must be one of {role_enum}, got '{source.get('role')}'")

    # --- target_agent (optional, but validate if present) ---
    target = data.get("target_agent")
    if target is not None and isinstance(target, dict):
        tgt_props = schema.get("target_agent", {}).get("properties", {})
        tgt_role_enum = tgt_props.get("role", {}).get("enum", [])
        if target.get("role") and target.get("role") not in tgt_role_enum:
            errors.append(f"target_agent.role must be one of {tgt_role_enum}")

    # --- message_type ---
    mt_enum = schema.get("message_type", {}).get("enum", [])
    if data.get("message_type") not in mt_enum:
        errors.append(f"message_type must be one of {mt_enum}, got '{data.get('message_type')}'")

    # --- protocol ---
    proto_enum = schema.get("protocol", {}).get("enum", [])
    proto = data.get("protocol")
    if proto is not None and proto not in proto_enum:
        errors.append(f"protocol must be one of {proto_enum}, got '{proto}'")

    # --- payload ---
    payload_schema = schema.get("payload", {})
    payload = data.get("payload", {})
    if "action" not in payload:
        errors.append("payload missing required 'action' field")
    
    # Validate coordinates within payload if present
    coords = payload.get("coordinates")
    if coords is not None:
        coord_props = payload_schema.get("properties", {}).get("coordinates", {}).get("properties", {})
        if "x" not in coords:
            errors.append("payload.coordinates missing 'x'")
        if "y" not in coords:
            errors.append("payload.coordinates missing 'y'")
        if "agent_id" not in coords:
            errors.append("payload.coordinates missing 'agent_id'")

    # Validate attachments within payload if present
    attachments = payload.get("attachments")
    if attachments is not None:
        if not isinstance(attachments, list):
            errors.append("payload.attachments must be a list")
        else:
            att_required = ("properties" in payload_schema and 
                          "attachments" in payload_schema["properties"] and
                          "items" in payload_schema["properties"]["attachments"])
            if att_required:
                att_fields = (payload_schema["properties"]["attachments"]
                             ["items"].get("required", []))
                for idx, att in enumerate(attachments):
                    for field in att_fields:
                        if field not in att:
                            errors.append(f"payload.attachments[{idx}] missing '{field}'")

    return len(errors) == 0, errors
