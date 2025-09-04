import os
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from parser import parse_file, get_supported_extensions
from memory import build_memory, reprocess_memory_session

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEMORY_RAW_DIR = BASE_DIR / "memory/raw"
MEMORY_SESSIONS_DIR = BASE_DIR / "memory/SESSIONS"
MEMORY_METADATA_FILE = BASE_DIR / "memory/processing_metadata.json"

# Ensure directories exist
MEMORY_RAW_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

def load_processing_metadata() -> Dict:
    """Load processing metadata from JSON file"""
    if MEMORY_METADATA_FILE.exists():
        try:
            with open(MEMORY_METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_processing_metadata(metadata: Dict) -> None:
    """Save processing metadata to JSON file"""
    try:
        with open(MEMORY_METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving metadata: {e}")

def ingest_and_process(file_path: str, system_name: str = "untitled", reprocess: bool = False) -> Dict:
    """
    Enhanced ingestion with reprocessing support and comprehensive metadata tracking.
    
    Args:
        file_path: Path to the file to process
        system_name: Name for the session
        reprocess: Whether this is a reprocessing operation
    
    Returns:
        Dict with processing results and metadata
    """
    try:
        raw_path = Path(file_path)
        if not raw_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate file type
        supported_extensions = get_supported_extensions()
        if raw_path.suffix.lower() not in supported_extensions:
            return {
                "status": "error",
                "message": f"Unsupported file type: {raw_path.suffix}. Supported: {', '.join(supported_extensions)}"
            }

        # Generate session info
        today = datetime.today().strftime('%Y-%m-%d')
        safe_name = system_name.strip().replace(" ", "-").lower()
        session_name = f"{today}-{safe_name}"
        session_dir = MEMORY_SESSIONS_DIR / session_name
        
        # Handle reprocessing
        if reprocess and session_dir.exists():
            try:
                processing_stats = reprocess_memory_session(session_dir)
                return {
                    "status": "success",
                    "message": "Session reprocessed successfully",
                    "session_name": session_name,
                    "session_dir": str(session_dir),
                    "output_path": str(session_dir / "memory.md"),
                    "processing_stats": processing_stats,
                    "reprocessed": True
                }
            except Exception as e:
                return {"status": "error", "message": f"Reprocessing failed: {str(e)}"}

        # Create session directory
        session_dir.mkdir(parents=True, exist_ok=True)

        # Copy to raw folder with unique name
        unique_name = f"{uuid.uuid4()}_{raw_path.name}"
        saved_path = MEMORY_RAW_DIR / unique_name
        saved_path.write_bytes(raw_path.read_bytes())

        # Save raw content for potential reprocessing
        raw_content_path = session_dir / "raw_content.txt"
        raw_content_path.write_bytes(raw_path.read_bytes())

        # Parse file with enhanced metadata
        parsed_content = parse_file(saved_path)

        # Build memory with enhanced processing
        output_path = session_dir / "memory.md"
        processing_stats = build_memory(parsed_content, output_path, reprocess=False)

        # Save processing metadata
        metadata = load_processing_metadata()
        metadata[session_name] = {
            "original_file": str(raw_path),
            "saved_raw": str(saved_path),
            "session_dir": str(session_dir),
            "processing_stats": processing_stats,
            "created_at": datetime.now().isoformat(),
            "file_metadata": parsed_content.get('metadata', {})
        }
        save_processing_metadata(metadata)

        return {
            "status": "success",
            "message": "File processed successfully",
            "session_name": session_name,
            "session_dir": str(session_dir),
            "output_path": str(output_path),
            "processing_stats": processing_stats,
            "file_metadata": parsed_content.get('metadata', {}),
            "reprocessed": False
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_session_info(session_name: str) -> Optional[Dict]:
    """Get information about a specific session"""
    metadata = load_processing_metadata()
    return metadata.get(session_name)

def list_all_sessions() -> Dict:
    """List all memory sessions with their metadata"""
    metadata = load_processing_metadata()
    sessions = {}
    
    for session_name, session_data in metadata.items():
        session_dir = Path(session_data.get('session_dir', ''))
        memory_file = session_dir / "memory.md"
        
        sessions[session_name] = {
            "name": session_name,
            "created_at": session_data.get('created_at'),
            "original_file": session_data.get('original_file'),
            "memory_file_exists": memory_file.exists(),
            "processing_stats": session_data.get('processing_stats', {}),
            "file_metadata": session_data.get('file_metadata', {})
        }
    
    return sessions

def delete_session(session_name: str) -> Dict:
    """Delete a memory session and its files"""
    try:
        metadata = load_processing_metadata()
        if session_name not in metadata:
            return {"status": "error", "message": f"Session {session_name} not found"}
        
        session_data = metadata[session_name]
        session_dir = Path(session_data.get('session_dir', ''))
        
        # Remove session directory
        if session_dir.exists():
            import shutil
            shutil.rmtree(session_dir)
        
        # Remove from metadata
        del metadata[session_name]
        save_processing_metadata(metadata)
        
        return {
            "status": "success",
            "message": f"Session {session_name} deleted successfully"
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Failed to delete session: {str(e)}"}

def get_processing_stats() -> Dict:
    """Get overall processing statistics"""
    metadata = load_processing_metadata()
    
    total_sessions = len(metadata)
    total_items = sum(
        session_data.get('processing_stats', {}).get('total_items', 0)
        for session_data in metadata.values()
    )
    
    file_types = {}
    for session_data in metadata.values():
        file_type = session_data.get('file_metadata', {}).get('file_type', 'unknown')
        file_types[file_type] = file_types.get(file_type, 0) + 1
    
    return {
        "total_sessions": total_sessions,
        "total_items_extracted": total_items,
        "file_types_processed": file_types,
        "supported_extensions": get_supported_extensions()
    }