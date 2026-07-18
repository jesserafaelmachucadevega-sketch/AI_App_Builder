#!/usr/bin/env python3
"""
OpenHands Unified Agent System - Main Entry Point

Integrates:
- Unified Message Bus (UDP/WebSocket)
- 2D Coordinate Tracker (tkinter)
- Local Workspace Volume Mount

Usage:
    python main.py                    # Full system with UI
    python main.py --no-ui           # Headless mode (bus only)
    python main.py --bus-only        # Message bus only
    python main.py --workspace-only  # Setup workspace only
"""

import argparse
import signal
import sys
import threading
import time
from typing import Optional

# Import components
from schemas.message_envelope import (
    MessageEnvelope,
    MessageType,
    AgentRole,
    CoordinateVector,
    Payload
)
from message_bus import (
    MessageBus,
    BusConfig,
    create_coordinate_message,
    create_file_modification_message
)
from tracker import CoordinateTracker
from workspace import (
    WorkspaceVolume,
    LibreOfficeConverter,
    CoderFileManager,
    setup_workspace,
    DEFAULT_WORKSPACE_BASE
)


class OpenHandsSystem:
    """
    Main system controller that orchestrates all components.
    """
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.running = False
        
        # Components
        self.message_bus: Optional[MessageBus] = None
        self.tracker: Optional[CoordinateTracker] = None
        self.workspace: Optional[WorkspaceVolume] = None
        self.coder_manager: Optional[CoderFileManager] = None
        self.converter: Optional[LibreOfficeConverter] = None
        
        # Agent state (for demo)
        self.agent_positions = {}
    
    def setup_workspace(self):
        """Initialize the workspace volume mount."""
        print("[System] Setting up workspace...")
        
        base_path = self.args.workspace_path or DEFAULT_WORKSPACE_BASE
        self.workspace = setup_workspace(base_path)
        
        if self.workspace._initialized:
            self.converter = LibreOfficeConverter(self.workspace.coder_output)
            self.coder_manager = CoderFileManager(self.workspace, self.converter)
            
            print(f"[System] Workspace ready: {base_path}")
            print(f"  - Coder input:  {self.workspace.coder_input}")
            print(f"  - Coder output: {self.workspace.coder_output}")
            print(f"  - LibreOffice:  {'Available' if self.converter.is_available else 'Not installed'}")
            return True
        return False
    
    def setup_message_bus(self):
        """Initialize the message bus."""
        print("[System] Starting message bus...")
        
        config = BusConfig(
            udp_host=self.args.udp_host,
            udp_port=self.args.udp_port,
            websocket_host=self.args.ws_host,
            websocket_port=self.args.ws_port,
            enable_udp=not self.args.no_udp,
            enable_websocket=not self.args.no_websocket
        )
        
        self.message_bus = MessageBus(config)
        
        # Register default handlers
        self.message_bus.register_handler(
            MessageType.COORDINATE_UPDATE.value,
            self._handle_coordinate_update
        )
        self.message_bus.register_handler(
            MessageType.FILE_MODIFICATION.value,
            self._handle_file_modification
        )
        self.message_bus.register_handler(
            MessageType.AGENT_REQUEST.value,
            self._handle_agent_request
        )
        
        # Register coordinate callbacks
        self.message_bus.on_coordinate_update(self._on_coordinate_update)
        self.message_bus.on_file_modification(self._on_file_modification)
        
        self.message_bus.start()
        print("[System] Message bus running")
        return True
    
    def setup_tracker(self):
        """Initialize the coordinate tracker UI."""
        print("[System] Starting 2D Coordinate Tracker...")
        
        self.tracker = CoordinateTracker(self.message_bus)
        self.tracker.start()
        
        print("[System] Coordinate tracker UI running")
        return True
    
    def _handle_coordinate_update(self, envelope: MessageEnvelope):
        """Handle incoming coordinate update."""
        source = envelope.source_agent
        coords = envelope.payload.coordinates
        
        if coords:
            agent_id = source.get('id', 'unknown')
            self.agent_positions[agent_id] = (coords.x, coords.y)
            print(f"[System] Agent {agent_id} position: ({coords.x:.1f}, {coords.y:.1f})")
    
    def _handle_file_modification(self, envelope: MessageEnvelope):
        """Handle file modification event."""
        source = envelope.source_agent
        attachments = envelope.payload.attachments
        
        for attachment in attachments:
            print(f"[System] Agent {source.get('id')} modified: {attachment.filename}")
            
            # If this is a coder agent, process the file
            if source.get('role') == 'coder' and self.coder_manager:
                # Trigger coordinate update based on file activity
                self._update_coder_position(attachment.filename)
    
    def _handle_agent_request(self, envelope: MessageEnvelope):
        """Handle agent request messages."""
        source = envelope.source_agent
        action = envelope.payload.action
        
        print(f"[System] Agent {source.get('id')} requested: {action}")
        
        # Process workspace requests
        if self.coder_manager and envelope.payload.resource:
            resource = envelope.payload.resource
            if action == "read_file":
                content = self.coder_manager.read_file(resource)
                if content:
                    self._send_response(envelope, {"status": "ok", "content_length": len(content)})
            elif action == "write_file":
                data = envelope.payload.data
                if data and 'content' in data:
                    path = self.coder_manager.write_file(resource, data['content'])
                    if path:
                        self._send_response(envelope, {"status": "ok", "path": str(path)})
    
    def _on_coordinate_update(self, envelope: MessageEnvelope, coordinates: CoordinateVector):
        """Callback when coordinates are updated."""
        if self.tracker and self.tracker.matrix:
            source = envelope.source_agent
            self.tracker.matrix.update_agent_position(
                agent_id=source.get('id', 'unknown'),
                role=source.get('role', 'unknown'),
                x=coordinates.x,
                y=coordinates.y
            )
    
    def _on_file_modification(self, envelope: MessageEnvelope, attachment):
        """Callback when files are modified."""
        if self.tracker:
            source = envelope.source_agent
            
            # Update agent position based on file activity
            self._update_coder_position(attachment.filename)
    
    def _update_coder_position(self, filename: str):
        """Update coder position based on file activity."""
        import hashlib
        
        # Generate position from filename hash
        hash_val = int(hashlib.md5(filename.encode()).hexdigest()[:4], 16)
        x = (hash_val % 100)
        y = 100 - ((hash_val // 100) % 100)
        
        if self.message_bus:
            msg = create_coordinate_message(
                agent_id="coder-1",
                agent_role="coder",
                x=x,
                y=y,
                metadata={"last_file": filename}
            )
            self.message_bus.send_udp(msg)
    
    def _send_response(self, request: MessageEnvelope, data: dict):
        """Send response to an agent request."""
        if self.message_bus:
            response = MessageEnvelope(
                source_agent={"id": "system", "role": "coordinator"},
                target_agent=request.source_agent,
                message_type=MessageType.AGENT_RESPONSE.value,
                payload=Payload(action="response", data=data),
                metadata={"request_id": request.message_id}
            )
            self.message_bus.send_udp(response)
    
    def start(self):
        """Start the system."""
        print("=" * 60)
        print("OpenHands Unified Agent System")
        print("=" * 60)
        
        self.running = True
        
        # Setup components based on args
        # Workspace: always set up unless --bus-only (which means bus ONLY, no workspace)
        if not self.args.bus_only:
            self.setup_workspace()
        
        # Message Bus: set up unless --workspace-only (which means workspace ONLY, no bus)
        if not self.args.workspace_only:
            self.setup_message_bus()
        
        # Tracker: set up in full mode only (not bus-only, not workspace-only, not no-ui)
        if not self.args.bus_only and not self.args.workspace_only and not self.args.no_ui:
            self.setup_tracker()
        
        print("=" * 60)
        print("System ready!")
        print("-" * 60)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Main loop (for demo/test)
        self._main_loop()
    
    def _main_loop(self):
        """Main loop for headless mode or monitoring."""
        print("[System] Entering main loop (Ctrl+C to stop)...")
        
        demo_agents = [
            ("agent-1", "coordinator", 20, 80),
            ("agent-2", "coder", 50, 50),
            ("agent-3", "reviewer", 80, 20),
            ("agent-4", "executor", 35, 65),
            ("agent-5", "monitor", 65, 35),
        ]
        
        tick = 0
        while self.running:
            time.sleep(2)
            tick += 1
            
            # Demo: Send periodic coordinate updates
            if self.args.demo and self.message_bus and tick % 3 == 0:
                for agent_id, role, base_x, base_y in demo_agents:
                    # Add some movement
                    import math
                    x = base_x + 10 * math.sin(tick / 5)
                    y = base_y + 10 * math.cos(tick / 5)
                    
                    msg = create_coordinate_message(
                        agent_id=agent_id,
                        agent_role=role,
                        x=x,
                        y=y
                    )
                    self.message_bus.send_udp(msg)
            
            # Check if tracker is still running
            if self.tracker and not self.tracker._running:
                self.running = False
                break
    
    def stop(self):
        """Stop the system."""
        print("\n[System] Shutting down...")
        self.running = False
        
        if self.message_bus:
            self.message_bus.stop()
        
        if self.tracker:
            self.tracker.stop()
        
        print("[System] System stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n[System] Received signal {signum}")
        self.stop()
        sys.exit(0)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="OpenHands Unified Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Full system with UI
  %(prog)s --no-ui             # Headless mode (bus + workspace)
  %(prog)s --bus-only          # Message bus only
  %(prog)s --demo              # Run with demo agent updates
  %(prog)s --workspace-only    # Setup workspace only
        """
    )
    
    # Mode options
    parser.add_argument('--no-ui', action='store_true',
                       help='Run without tkinter UI')
    parser.add_argument('--bus-only', action='store_true',
                       help='Run message bus only')
    parser.add_argument('--workspace-only', action='store_true',
                       help='Setup workspace only')
    parser.add_argument('--demo', action='store_true',
                       help='Run demo with simulated agent updates')
    
    # Network options
    parser.add_argument('--udp-host', default='0.0.0.0',
                       help='UDP bind host (default: 0.0.0.0)')
    parser.add_argument('--udp-port', type=int, default=5005,
                       help='UDP port (default: 5005)')
    parser.add_argument('--ws-host', default='0.0.0.0',
                       help='WebSocket bind host (default: 0.0.0.0)')
    parser.add_argument('--ws-port', type=int, default=8765,
                       help='WebSocket port (default: 8765)')
    parser.add_argument('--no-udp', action='store_true',
                       help='Disable UDP listener')
    parser.add_argument('--no-websocket', action='store_true',
                       help='Disable WebSocket server')
    
    # Workspace options
    parser.add_argument('--workspace-path', 
                       default=DEFAULT_WORKSPACE_BASE,
                       help=f'Workspace base path (default: {DEFAULT_WORKSPACE_BASE})')
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    system = OpenHandsSystem(args)
    
    try:
        system.start()
    except KeyboardInterrupt:
        system.stop()
    except Exception as e:
        print(f"[System] Error: {e}")
        system.stop()
        raise


if __name__ == "__main__":
    main()
