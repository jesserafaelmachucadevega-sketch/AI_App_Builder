"""
Local Workspace Volume Mount Manager

Handles persistent storage for the OpenHands workspace.
Manages the /home/jesse/openhands_workspace directory structure
and provides file conversion utilities for the Coder agent.
"""

import os
import shutil
import hashlib
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Callable
from datetime import datetime


# Default workspace base path
DEFAULT_WORKSPACE_BASE = "/home/jesse/openhands_workspace"


@dataclass
class FileInfo:
    """Information about a file in the workspace."""
    path: str
    filename: str
    size_bytes: int
    mime_type: str
    created_at: datetime
    modified_at: datetime
    checksum: Optional[str] = None


class WorkspaceVolume:
    """
    Manages the local workspace volume mount.
    
    Directory structure:
    /home/jesse/openhands_workspace/
    ├── coder/           # Coder agent workspace
    │   ├── input/       # Raw input files (LibreOffice, etc.)
    │   ├── output/      # Processed/converted files
    │   ├── drafts/      # Work in progress
    │   └── cache/       # Temporary/cache files
    ├── coordinator/     # Coordinator agent workspace
    ├── executor/        # Executor agent workspace
    ├── reviewer/        # Reviewer agent workspace
    └── shared/          # Shared resources between agents
    """
    
    def __init__(self, base_path: str = DEFAULT_WORKSPACE_BASE):
        self.base_path = Path(base_path)
        self.coder_path = self.base_path / "coder"
        self.coder_input = self.coder_path / "input"
        self.coder_output = self.coder_path / "output"
        self.coder_drafts = self.coder_path / "drafts"
        self.coder_cache = self.coder_path / "cache"
        
        self.shared_path = self.base_path / "shared"
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the workspace directory structure.
        Creates all necessary directories with proper permissions.
        """
        try:
            # Create base directory
            self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Create agent directories
            agent_dirs = [
                self.base_path / "coordinator",
                self.base_path / "executor",
                self.base_path / "reviewer",
                self.base_path / "monitor",
            ]
            
            for agent_dir in agent_dirs:
                agent_dir.mkdir(parents=True, exist_ok=True)
            
            # Create coder subdirectories
            for subdir in [self.coder_input, self.coder_output, 
                          self.coder_drafts, self.coder_cache]:
                subdir.mkdir(parents=True, exist_ok=True)
            
            # Create shared directory
            self.shared_path.mkdir(parents=True, exist_ok=True)
            
            self._initialized = True
            print(f"[Workspace] Initialized at {self.base_path}")
            return True
            
        except PermissionError as e:
            print(f"[Workspace] Permission denied: {e}")
            return False
        except Exception as e:
            print(f"[Workspace] Initialization failed: {e}")
            return False
    
    def get_coder_input_path(self, filename: str) -> Path:
        """Get full path for a coder input file."""
        return self.coder_input / filename
    
    def get_coder_output_path(self, filename: str) -> Path:
        """Get full path for a coder output file."""
        return self.coder_output / filename
    
    def get_agent_path(self, agent_role: str) -> Path:
        """Get workspace path for a specific agent."""
        return self.base_path / agent_role.lower()
    
    def list_files(self, directory: Optional[Path] = None, 
                   pattern: str = "*") -> List[FileInfo]:
        """List files in a directory with metadata."""
        if directory is None:
            directory = self.coder_input
            
        files = []
        for path in directory.glob(pattern):
            if path.is_file():
                stat = path.stat()
                files.append(FileInfo(
                    path=str(path),
                    filename=path.name,
                    size_bytes=stat.st_size,
                    mime_type=self._guess_mime_type(path),
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                    checksum=self._calculate_checksum(path)
                ))
        return files
    
    def _guess_mime_type(self, path: Path) -> str:
        """Guess MIME type from file extension."""
        mime_types = {
            '.odt': 'application/vnd.oasis.opendocument.text',
            '.ods': 'application/vnd.oasis.opendocument.spreadsheet',
            '.odp': 'application/vnd.oasis.opendocument.presentation',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.json': 'application/json',
            '.xml': 'application/xml',
        }
        return mime_types.get(path.suffix.lower(), 'application/octet-stream')
    
    def _calculate_checksum(self, path: Path) -> str:
        """Calculate MD5 checksum of a file."""
        md5 = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()
    
    def safe_copy(self, src: Path, dest: Path, overwrite: bool = False) -> bool:
        """Safely copy a file with validation."""
        if not src.exists():
            print(f"[Workspace] Source file not found: {src}")
            return False
            
        if dest.exists() and not overwrite:
            print(f"[Workspace] Destination exists: {dest}")
            return False
            
        try:
            shutil.copy2(src, dest)
            print(f"[Workspace] Copied: {src} -> {dest}")
            return True
        except Exception as e:
            print(f"[Workspace] Copy failed: {e}")
            return False


class LibreOfficeConverter:
    """
    Converts LibreOffice formats (ODT, ODS, ODP) to other formats.
    
    Requires LibreOffice to be installed on the system.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.libreoffice_paths = [
            'libreoffice',
            'soffice',
            '/usr/bin/libreoffice',
            '/usr/bin/soffice',
            '/Applications/LibreOffice.app/Contents/MacOS/soffice'
        ]
        self.libreoffice_cmd = self._find_libreoffice()
        self.output_dir = output_dir
    
    def _find_libreoffice(self) -> Optional[str]:
        """Find LibreOffice executable."""
        for cmd in self.libreoffice_paths:
            try:
                result = subprocess.run([cmd, '--version'], 
                                       capture_output=True, 
                                       timeout=5)
                if result.returncode == 0:
                    print(f"[Converter] Found LibreOffice: {result.stdout.decode().strip()}")
                    return cmd
            except (subprocess.SubprocessError, FileNotFoundError):
                continue
        return None
    
    @property
    def is_available(self) -> bool:
        """Check if LibreOffice is available."""
        return self.libreoffice_cmd is not None
    
    def convert(self, input_file: Path, output_format: str,
                output_dir: Optional[Path] = None,
                timeout: int = 60) -> Optional[Path]:
        """
        Convert a file to the specified format.
        
        Args:
            input_file: Path to input file (ODT, ODS, ODP, DOCX, etc.)
            output_format: Target format (pdf, docx, txt, html, etc.)
            output_dir: Output directory (defaults to input file's directory)
            timeout: Conversion timeout in seconds
            
        Returns:
            Path to converted file, or None if conversion failed
        """
        if not self.is_available:
            print("[Converter] LibreOffice not found")
            return None
            
        if not input_file.exists():
            print(f"[Converter] Input file not found: {input_file}")
            return None
            
        output_dir = output_dir or input_file.parent
        
        try:
            # Build command
            cmd = [
                self.libreoffice_cmd,
                '--headless',
                '--convert-to', output_format,
                '--outdir', str(output_dir),
                str(input_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                # Find output file
                base_name = input_file.stem
                output_file = output_dir / f"{base_name}.{output_format}"
                
                if output_file.exists():
                    print(f"[Converter] Converted: {input_file.name} -> {output_file.name}")
                    return output_file
                else:
                    print(f"[Converter] Output file not created")
                    return None
            else:
                print(f"[Converter] Conversion failed: {result.stderr.decode()}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"[Converter] Conversion timed out after {timeout}s")
            return None
        except Exception as e:
            print(f"[Converter] Error: {e}")
            return None
    
    def supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        return ['pdf', 'docx', 'odt', 'txt', 'html', 'rtf', 'csv', 'xlsx', 'ods', 'pptx', 'odp']


class CoderFileManager:
    """
    Manages file operations for the Coder agent.
    
    Handles reading, writing, and converting raw document files
    (LibreOffice formats) using automated conversion scripts.
    """
    
    def __init__(self, workspace: WorkspaceVolume, converter: Optional[LibreOfficeConverter] = None):
        self.workspace = workspace
        self.converter = converter or LibreOfficeConverter(workspace.coder_output)
        self._file_handlers: dict[str, Callable] = {}
    
    def register_handler(self, mime_type: str, handler: Callable[[Path], Optional[Path]]):
        """Register a custom handler for specific MIME type."""
        self._file_handlers[mime_type] = handler
    
    def read_file(self, filename: str, convert_to: Optional[str] = None) -> Optional[str]:
        """
        Read a file from the coder input directory.
        
        Args:
            filename: Name of the file to read
            convert_to: Optional format to convert to before reading (e.g., 'txt', 'pdf')
            
        Returns:
            File content as string, or None if file not found or conversion failed
        """
        input_path = self.workspace.get_coder_input_path(filename)
        
        if not input_path.exists():
            print(f"[CoderManager] File not found: {filename}")
            return None
        
        # If conversion requested and we have a converter
        if convert_to and self.converter.is_available:
            converted = self.converter.convert(input_path, convert_to)
            if converted:
                input_path = converted
        
        try:
            # For text-based files
            if self.workspace._guess_mime_type(input_path).startswith('text/'):
                return input_path.read_text(encoding='utf-8')
            else:
                # For binary files, return path
                return str(input_path)
        except Exception as e:
            print(f"[CoderManager] Read error: {e}")
            return None
    
    def write_file(self, filename: str, content: str, 
                   draft: bool = False) -> Optional[Path]:
        """
        Write content to a file in the coder workspace.
        
        Args:
            filename: Name of the file to write
            content: Content to write
            draft: If True, write to drafts directory
            
        Returns:
            Path to written file, or None on error
        """
        target_dir = self.workspace.coder_drafts if draft else self.workspace.coder_output
        output_path = target_dir / filename
        
        try:
            output_path.write_text(content, encoding='utf-8')
            print(f"[CoderManager] Written: {output_path}")
            return output_path
        except Exception as e:
            print(f"[CoderManager] Write error: {e}")
            return None
    
    def process_input_file(self, filename: str, 
                          target_format: str = 'txt') -> Optional[Path]:
        """
        Process an input file by converting it to target format.
        
        Uses registered handlers if available, otherwise falls back to LibreOffice.
        """
        input_path = self.workspace.get_coder_input_path(filename)
        mime_type = self.workspace._guess_mime_type(input_path)
        
        # Check for custom handler
        if mime_type in self._file_handlers:
            return self._file_handlers[mime_type](input_path)
        
        # Use LibreOffice converter
        if self.converter.is_available:
            return self.converter.convert(input_path, target_format)
        else:
            print("[CoderManager] No converter available for file processing")
            return None
    
    def list_input_files(self) -> List[FileInfo]:
        """List all files in the coder input directory."""
        return self.workspace.list_files(self.workspace.coder_input)
    
    def list_output_files(self) -> List[FileInfo]:
        """List all files in the coder output directory."""
        return self.workspace.list_files(self.workspace.coder_output)


def setup_workspace(base_path: str = DEFAULT_WORKSPACE_BASE) -> WorkspaceVolume:
    """
    Setup the workspace volume with proper directory structure.
    
    Returns:
        Initialized WorkspaceVolume instance
    """
    workspace = WorkspaceVolume(base_path)
    if workspace.initialize():
        print(f"[Setup] Workspace ready at {base_path}")
        print(f"[Setup] Coder input: {workspace.coder_input}")
        print(f"[Setup] Coder output: {workspace.coder_output}")
    return workspace


if __name__ == "__main__":
    # Demo initialization
    ws = setup_workspace("/tmp/openhands_workspace_test")
    print("\nDirectory structure:")
    for path in ws.base_path.rglob("*"):
        if path.is_dir():
            print(f"  📁 {path}")
    
    # Test LibreOffice converter
    converter = LibreOfficeConverter()
    print(f"\nLibreOffice available: {converter.is_available}")
    if converter.is_available:
        print(f"Supported formats: {converter.supported_formats()}")
