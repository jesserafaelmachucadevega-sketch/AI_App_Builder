"""
2D Coordinate Tracker

Visualization layer for agent positions on a 2D matrix.
Integrates with the message bus for real-time updates.

Requires tkinter for GUI mode. Falls back to headless mode if unavailable.
"""

# Check if tkinter is available
TKINTER_AVAILABLE = False
tk = None
ttk = None
messagebox = None

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    pass

from typing import Optional, Callable, Dict, Tuple
from dataclasses import dataclass
import threading

try:
    from schemas.message_envelope import MessageEnvelope, CoordinateVector
    from message_bus import MessageBus
except ImportError:
    import sys
    sys.path.insert(0, '/workspace/project')
    from schemas.message_envelope import MessageEnvelope, CoordinateVector
    from message_bus import MessageBus


# Agent colors for visualization
AGENT_COLORS = {
    "coordinator": "#FF6B6B",  # Red
    "coder": "#4ECDC4",        # Teal
    "reviewer": "#45B7D1",     # Blue
    "executor": "#96CEB4",     # Green
    "monitor": "#FFEAA7",      # Yellow
}

DEFAULT_COLOR = "#DDA0DD"  # Plum


@dataclass
class AgentPoint:
    """Represents an agent's position on the 2D matrix."""
    agent_id: str
    role: str
    x: float
    y: float
    label: Optional[str] = None
    color: Optional[str] = None
    last_update: float = 0


if TKINTER_AVAILABLE:
    class CoordinateMatrix(tk.Canvas):
        """Custom canvas for 2D coordinate visualization."""
        
        def __init__(self, parent, width: int = 600, height: int = 600, **kwargs):
            super().__init__(parent, width=width, height=height, bg="#1a1a2e", **kwargs)
            self.width = width
            self.height = height
            self.agents: Dict[str, AgentPoint] = {}
            self.coordinate_ranges = {
                'x_min': 0, 'x_max': 100,
                'y_min': 0, 'y_max': 100
            }
            self.point_radius = 15
            self._setup_grid()
            
        def _setup_grid(self):
            """Draw the background grid."""
            # Draw border
            self.create_rectangle(50, 50, self.width - 50, self.height - 50, 
                                 outline="#4a4a6a", width=2)
            
            # Draw grid lines
            for i in range(1, 10):
                x = 50 + (self.width - 100) * i / 10
                y = 50 + (self.height - 100) * i / 10
                self.create_line(x, 50, x, self.height - 50, fill="#2a2a4a", dash=(2, 4))
                self.create_line(50, y, self.width - 50, y, fill="#2a2a4a", dash=(2, 4))
            
            # Draw axis labels
            self.create_text(self.width / 2, 30, text="2D Agent Coordinate Matrix", 
                            fill="white", font=("Arial", 14, "bold"))
            self.create_text(25, self.height / 2, text="Y", fill="white", font=("Arial", 12))
            self.create_text(self.width / 2, self.height - 25, text="X", fill="white", font=("Arial", 12))
            
            # Axis tick labels
            for i in range(0, 101, 25):
                x_pos = 50 + (self.width - 100) * i / 100
                y_pos = self.height - 50 - (self.height - 100) * i / 100
                self.create_text(x_pos, self.height - 35, text=str(i), fill="#888888", font=("Arial", 8))
                self.create_text(35, y_pos, text=str(i), fill="#888888", font=("Arial", 8))
        
        def _coord_to_pixel(self, x: float, y: float) -> Tuple[int, int]:
            """Convert coordinate values to pixel positions."""
            x_range = self.coordinate_ranges['x_max'] - self.coordinate_ranges['x_min']
            y_range = self.coordinate_ranges['y_max'] - self.coordinate_ranges['y_min']
            
            x_ratio = (x - self.coordinate_ranges['x_min']) / x_range
            y_ratio = (y - self.coordinate_ranges['y_min']) / y_range
            
            px = 50 + (self.width - 100) * x_ratio
            py = self.height - 50 - (self.height - 100) * y_ratio
            
            return int(px), int(py)
        
        def set_coordinate_range(self, x_min: float, x_max: float, y_min: float, y_max: float):
            """Set the visible coordinate range."""
            self.coordinate_ranges = {'x_min': x_min, 'x_max': x_max, 
                                      'y_min': y_min, 'y_max': y_max}
            self.redraw()
        
        def update_agent_position(self, agent_id: str, role: str, x: float, y: float, 
                                  label: Optional[str] = None):
            """Update or add an agent's position on the matrix."""
            import time
            
            color = AGENT_COLORS.get(role.lower(), DEFAULT_COLOR)
            
            if agent_id in self.agents:
                # Update existing agent
                self.agents[agent_id].x = x
                self.agents[agent_id].y = y
                self.agents[agent_id].last_update = time.time()
            else:
                # Add new agent
                self.agents[agent_id] = AgentPoint(
                    agent_id=agent_id,
                    role=role,
                    x=x,
                    y=y,
                    label=label or agent_id,
                    color=color
                )
            
            self.redraw()
        
        def remove_agent(self, agent_id: str):
            """Remove an agent from the matrix."""
            if agent_id in self.agents:
                del self.agents[agent_id]
                self.redraw()
        
        def redraw(self):
            """Redraw all agents on the matrix."""
            # Clear all items except grid (we'll redraw grid too)
            self.delete("all")
            self._setup_grid()
            
            # Draw all agents
            for agent in self.agents.values():
                px, py = self._coord_to_pixel(agent.x, agent.y)
                
                # Draw point
                self.create_oval(
                    px - self.point_radius, py - self.point_radius,
                    px + self.point_radius, py + self.point_radius,
                    fill=agent.color, outline="white", width=2, tags=f"agent_{agent.agent_id}"
                )
                
                # Draw label
                self.create_text(px, py, text=agent.label[:3].upper(), 
                               fill="white", font=("Arial", 8, "bold"), tags=f"label_{agent.agent_id}")
                
                # Draw agent ID below
                self.create_text(px, py + self.point_radius + 12, 
                               text=agent.agent_id[:8], fill="#aaaaaa", font=("Arial", 7))
else:
    # Headless mode - just a data container
    class CoordinateMatrix:
        """Headless coordinate matrix for environments without tkinter."""
        
        def __init__(self, parent=None, width: int = 600, height: int = 600, **kwargs):
            self.width = width
            self.height = height
            self.agents: Dict[str, AgentPoint] = {}
            self.coordinate_ranges = {'x_min': 0, 'x_max': 100, 'y_min': 0, 'y_max': 100}
            print("[Tracker] Running in headless mode (tkinter not available)")
        
        def set_coordinate_range(self, x_min, x_max, y_min, y_max):
            self.coordinate_ranges = {'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max}
        
        def update_agent_position(self, agent_id: str, role: str, x: float, y: float, label: Optional[str] = None):
            color = AGENT_COLORS.get(role.lower(), DEFAULT_COLOR)
            self.agents[agent_id] = AgentPoint(
                agent_id=agent_id, role=role, x=x, y=y, label=label or agent_id, color=color
            )
            print(f"[Tracker] Agent {agent_id} ({role}): ({x:.1f}, {y:.1f})")
        
        def remove_agent(self, agent_id: str):
            if agent_id in self.agents:
                del self.agents[agent_id]
        
        def redraw(self):
            pass
        
        def pack(self, **kwargs):
            pass


if TKINTER_AVAILABLE:
    class CoordinateTracker:
        """
        2D Coordinate Tracker with tkinter UI.
        
        Connects to the message bus and updates the visualization
        in real-time when agents modify files or state.
        """
        
        def __init__(self, message_bus: Optional[MessageBus] = None):
            self.message_bus = message_bus
            self.root: Optional[tk.Tk] = None
            self.matrix: Optional[CoordinateMatrix] = None
            self.log_widget: Optional[tk.Text] = None
            self.status_label: Optional[tk.Label] = None
            self._running = False
            
            # Register callbacks if bus is provided
            if self.message_bus:
                self._register_bus_callbacks()
        
        def _register_bus_callbacks(self):
            """Register callbacks with the message bus."""
            self.message_bus.on_coordinate_update(self._on_coordinate_update)
            self.message_bus.on_file_modification(self._on_file_modification)
        
        def _on_coordinate_update(self, envelope: MessageEnvelope, coordinates: CoordinateVector):
            """Handle coordinate update from message bus."""
            if self.root and self.matrix:
                source = envelope.source_agent
                self.root.after(0, lambda: self.matrix.update_agent_position(
                    agent_id=source.get('id', 'unknown'),
                    role=source.get('role', 'unknown'),
                    x=coordinates.x,
                    y=coordinates.y
                ))
                self.log_message(f"Coordinate update: {source.get('id')} -> ({coordinates.x:.1f}, {coordinates.y:.1f})")
        
        def _on_file_modification(self, envelope: MessageEnvelope, attachment):
            """Handle file modification from message bus."""
            source = envelope.source_agent
            self.log_message(f"File modified by {source.get('id')}: {attachment.filename}")
            
            # Update coordinate based on file modification
            # Using a simple hash-based position mapping
            import hashlib
            hash_val = int(hashlib.md5(attachment.path.encode()).hexdigest()[:4], 16)
            x = (hash_val % 100)
            y = 100 - ((hash_val // 100) % 100)
            
            if self.matrix:
                self.root.after(0, lambda: self.matrix.update_agent_position(
                    agent_id=source.get('id', 'unknown'),
                    role=source.get('role', 'unknown'),
                    x=x, y=y
                ))
        
        def log_message(self, message: str):
            """Add a message to the log widget."""
            if self.root and self.log_widget:
                from datetime import datetime
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_widget.insert(tk.END, f"[{timestamp}] {message}\n")
                self.log_widget.see(tk.END)
            else:
                print(f"[Tracker] {message}")
        
        def _setup_ui(self):
            """Setup the tkinter UI."""
            self.root = tk.Tk()
            self.root.title("2D Agent Coordinate Tracker")
            self.root.geometry("900x700")
            self.root.configure(bg="#0f0f1a")
            
            # Main container
            main_frame = ttk.Frame(self.root)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Header
            header = tk.Frame(main_frame, bg="#0f0f1a")
            header.pack(fill=tk.X)
            tk.Label(header, text="Unified Agent Coordinate Visualization", 
                    bg="#0f0f1a", fg="white", font=("Arial", 16, "bold")).pack()
            
            # Control panel
            control_frame = ttk.LabelFrame(main_frame, text="Controls")
            control_frame.pack(fill=tk.X, pady=(10, 0))
            
            # Coordinate range controls
            range_frame = ttk.Frame(control_frame)
            range_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Label(range_frame, text="X Range:").grid(row=0, column=0, sticky=tk.W)
            self.x_min_entry = ttk.Entry(range_frame, width=6)
            self.x_min_entry.insert(0, "0")
            self.x_min_entry.grid(row=0, column=1, padx=2)
            ttk.Label(range_frame, text="to").grid(row=0, column=2)
            self.x_max_entry = ttk.Entry(range_frame, width=6)
            self.x_max_entry.insert(0, "100")
            self.x_max_entry.grid(row=0, column=3, padx=2)
            
            ttk.Label(range_frame, text="Y Range:").grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
            self.y_min_entry = ttk.Entry(range_frame, width=6)
            self.y_min_entry.insert(0, "0")
            self.y_min_entry.grid(row=0, column=5, padx=2)
            ttk.Label(range_frame, text="to").grid(row=0, column=6)
            self.y_max_entry = ttk.Entry(range_frame, width=6)
            self.y_max_entry.insert(0, "100")
            self.y_max_entry.grid(row=0, column=7, padx=2)
            
            ttk.Button(range_frame, text="Apply", command=self._apply_range).grid(row=0, column=8, padx=10)
            ttk.Button(range_frame, text="Reset View", command=self._reset_view).grid(row=0, column=9)
            
            # Manual agent entry
            agent_frame = ttk.Frame(control_frame)
            agent_frame.pack(fill=tk.X, padx=5, pady=5)
            
            ttk.Label(agent_frame, text="Agent ID:").grid(row=0, column=0, sticky=tk.W)
            self.agent_id_entry = ttk.Entry(agent_frame, width=12)
            self.agent_id_entry.grid(row=0, column=1, padx=2)
            
            ttk.Label(agent_frame, text="Role:").grid(row=0, column=2, padx=(10, 0))
            self.agent_role_combo = ttk.Combobox(agent_frame, values=["coordinator", "coder", "reviewer", "executor", "monitor"], width=10)
            self.agent_role_combo.current(0)
            self.agent_role_combo.grid(row=0, column=3, padx=2)
            ttk.Label(agent_frame, text="X:").grid(row=0, column=4, padx=(10, 0))
            self.x_entry = ttk.Entry(agent_frame, width=6)
            self.x_entry.insert(0, "50")
            self.x_entry.grid(row=0, column=5, padx=2)
            
            ttk.Label(agent_frame, text="Y:").grid(row=0, column=6)
            self.y_entry = ttk.Entry(agent_frame, width=6)
            self.y_entry.insert(0, "50")
            self.y_entry.grid(row=0, column=7, padx=2)
            
            ttk.Button(agent_frame, text="Update Position", command=self._update_manual_position).grid(row=0, column=8, padx=10)
            
            # Canvas and log side by side
            content_frame = ttk.Frame(main_frame)
            content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # Matrix canvas
            canvas_frame = ttk.Frame(content_frame)
            canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            self.matrix = CoordinateMatrix(canvas_frame, width=600, height=500)
            self.matrix.pack()
            
            # Legend
            legend_frame = ttk.LabelFrame(content_frame, text="Agent Roles")
            legend_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
            
            for role, color in AGENT_COLORS.items():
                frame = tk.Frame(legend_frame, bg=color, width=20, height=20)
                frame.pack(padx=10, pady=2)
                tk.Label(legend_frame, text=role.capitalize(), font=("Arial", 9)).pack()
            
            # Log panel
            log_frame = ttk.LabelFrame(main_frame, text="Event Log")
            log_frame.pack(fill=tk.BOTH, expand=True)
            
            self.log_widget = tk.Text(log_frame, height=8, bg="#1a1a2e", fg="#00ff00", 
                                      font=("Courier", 9))
            scrollbar = ttk.Scrollbar(log_frame, command=self.log_widget.yview)
            self.log_widget.configure(yscrollcommand=scrollbar.set)
            self.log_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Status bar
            self.status_label = tk.Label(main_frame, text="Status: Ready", 
                                         bd=1, relief=tk.SUNKEN, anchor=tk.W)
            self.status_label.pack(fill=tk.X, pady=(5, 0))
            
            if self.message_bus:
                self.status_label.config(text="Status: Connected to Message Bus")
        
        def _apply_range(self):
            """Apply coordinate range from entry fields."""
            try:
                x_min = float(self.x_min_entry.get())
                x_max = float(self.x_max_entry.get())
                y_min = float(self.y_min_entry.get())
                y_max = float(self.y_max_entry.get())
                self.matrix.set_coordinate_range(x_min, x_max, y_min, y_max)
                self.log_message(f"Range updated: X[{x_min}-{x_max}], Y[{y_min}-{y_max}]")
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers")
        
        def _reset_view(self):
            """Reset to default view."""
            self.x_min_entry.delete(0, tk.END)
            self.x_min_entry.insert(0, "0")
            self.x_max_entry.delete(0, tk.END)
            self.x_max_entry.insert(0, "100")
            self.y_min_entry.delete(0, tk.END)
            self.y_min_entry.insert(0, "0")
            self.y_max_entry.delete(0, tk.END)
            self.y_max_entry.insert(0, "100")
            self.matrix.set_coordinate_range(0, 100, 0, 100)
            self.log_message("View reset to default")
        
        def _update_manual_position(self):
            """Update position from manual entry."""
            try:
                agent_id = self.agent_id_entry.get() or f"manual_{id(self)}"
                role = self.agent_role_combo.get()
                x = float(self.x_entry.get())
                y = float(self.y_entry.get())
                
                self.matrix.update_agent_position(agent_id, role, x, y)
                self.log_message(f"Manual update: {agent_id} ({role}) -> ({x}, {y})")
                
                # Also send to message bus if connected
                if self.message_bus:
                    from message_bus import create_coordinate_message
                    msg = create_coordinate_message(agent_id, role, x, y)
                    self.message_bus.send_udp(msg)
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid X and Y coordinates")
        
        def start(self):
            """Start the tkinter UI."""
            self._setup_ui()
            self._running = True
            self.log_message("2D Coordinate Tracker started")
            
            # Run in separate thread to not block
            thread = threading.Thread(target=self.root.mainloop, daemon=True)
            thread.start()
        
        def stop(self):
            """Stop the tkinter UI."""
            self._running = False
            if self.root:
                self.root.quit()
        
        def connect_bus(self, bus: MessageBus):
            """Connect to a message bus."""
            self.message_bus = bus
            self._register_bus_callbacks()
            if self.status_label:
                self.status_label.config(text="Status: Connected to Message Bus")

else:
    # Headless CoordinateTracker for environments without tkinter
    class CoordinateTracker:
        """Headless coordinate tracker for environments without GUI."""
        
        def __init__(self, message_bus: Optional[MessageBus] = None):
            self.message_bus = message_bus
            self.matrix = CoordinateMatrix()
            self._running = False
            print("[Tracker] Running in headless mode")
            
            if self.message_bus:
                self._register_bus_callbacks()
        
        def _register_bus_callbacks(self):
            self.message_bus.on_coordinate_update(self._on_coordinate_update)
            self.message_bus.on_file_modification(self._on_file_modification)
        
        def _on_coordinate_update(self, envelope: MessageEnvelope, coordinates: CoordinateVector):
            source = envelope.source_agent
            self.matrix.update_agent_position(
                agent_id=source.get('id', 'unknown'),
                role=source.get('role', 'unknown'),
                x=coordinates.x,
                y=coordinates.y
            )
        
        def _on_file_modification(self, envelope: MessageEnvelope, attachment):
            source = envelope.source_agent
            import hashlib
            hash_val = int(hashlib.md5(attachment.path.encode()).hexdigest()[:4], 16)
            x = (hash_val % 100)
            y = 100 - ((hash_val // 100) % 100)
            self.matrix.update_agent_position(
                agent_id=source.get('id', 'unknown'),
                role=source.get('role', 'unknown'),
                x=x, y=y
            )
        
        def log_message(self, message: str):
            print(f"[Tracker] {message}")
        
        def start(self):
            self._running = True
            self.log_message("2D Coordinate Tracker started (headless)")
        
        def stop(self):
            self._running = False
        
        def connect_bus(self, bus: MessageBus):
            self.message_bus = bus
            self._register_bus_callbacks()


if __name__ == "__main__":
    # Demo mode without message bus
    tracker = CoordinateTracker()
    tracker.start()
