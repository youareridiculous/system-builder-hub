"""
Export models and data structures
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from io import BytesIO

@dataclass
class ExportFile:
    """Represents a file in the export bundle"""
    path: str
    content: str
    size: int
    sha256: str
    mtime: datetime
    
    def __post_init__(self):
        if isinstance(self.mtime, str):
            self.mtime = datetime.fromisoformat(self.mtime)

@dataclass
class ExportManifest:
    """Export manifest with metadata"""
    project_id: str
    tenant_id: str
    export_timestamp: datetime
    sbh_version: str
    files: List[ExportFile]
    total_size: int
    checksum: str
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if isinstance(self.export_timestamp, str):
            self.export_timestamp = datetime.fromisoformat(self.export_timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['export_timestamp'] = self.export_timestamp.isoformat()
        data['files'] = [asdict(f) for f in self.files]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportManifest':
        """Create from dictionary"""
        files = [ExportFile(**f) for f in data.get('files', [])]
        return cls(
            project_id=data['project_id'],
            tenant_id=data['tenant_id'],
            export_timestamp=data['export_timestamp'],
            sbh_version=data['sbh_version'],
            files=files,
            total_size=data['total_size'],
            checksum=data['checksum'],
            metadata=data.get('metadata', {})
        )

@dataclass
class ExportBundle:
    """Complete export bundle"""
    manifest: ExportManifest
    files: Dict[str, str]  # path -> content
    
    def get_file_content(self, path: str) -> Optional[str]:
        """Get file content by path"""
        return self.files.get(path)
    
    def add_file(self, path: str, content: str, mtime: Optional[datetime] = None):
        """Add file to bundle"""
        if mtime is None:
            mtime = datetime.utcnow()
        
        size = len(content.encode('utf-8'))
        sha256 = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        export_file = ExportFile(
            path=path,
            content=content,
            size=size,
            sha256=sha256,
            mtime=mtime
        )
        
        self.files[path] = content
        self.manifest.files.append(export_file)
        self.manifest.total_size += size
    
    def update_checksum(self):
        """Update bundle checksum"""
        # Create deterministic checksum from sorted files
        file_checksums = sorted([f.sha256 for f in self.manifest.files])
        checksum_content = ''.join(file_checksums)
        self.manifest.checksum = hashlib.sha256(checksum_content.encode('utf-8')).hexdigest()

@dataclass
class ExportDiff:
    """Export diff between two manifests"""
    added: List[str]
    removed: List[str]
    changed: List[str]
    total_added: int
    total_removed: int
    total_changed: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
