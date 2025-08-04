"""
File service for handling file operations and realistic file generation
"""

import logging
import mimetypes
import os
import random
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FileService:
    """Service for handling file operations"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension from filename"""
        return Path(filename).suffix.lower()
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type for file"""
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
    def _generate_video_header(self, filename: str) -> bytes:
        """Generate realistic video file header"""
        ext = self._get_file_extension(filename)
        
        if ext == '.mp4':
            # MP4 header
            return b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom'
        elif ext == '.avi':
            # AVI header
            return b'RIFF\x00\x00\x00\x00AVI '
        elif ext == '.mkv':
            # MKV header
            return b'\x1a\x45\xdf\xa3'
        elif ext == '.mov':
            # MOV header
            return b'\x00\x00\x00\x20ftypqt  '
        else:
            # Generic video header
            return b'VIDEO' + b'\x00' * 27
    
    def _generate_audio_header(self, filename: str) -> bytes:
        """Generate realistic audio file header"""
        ext = self._get_file_extension(filename)
        
        if ext == '.mp3':
            # MP3 header
            return b'\xff\xfb\x90\x44'
        elif ext == '.wav':
            # WAV header
            return b'RIFF\x00\x00\x00\x00WAVEfmt '
        elif ext == '.flac':
            # FLAC header
            return b'fLaC'
        elif ext == '.ogg':
            # OGG header
            return b'OggS'
        else:
            # Generic audio header
            return b'AUDIO' + b'\x00' * 27
    
    def _generate_image_header(self, filename: str) -> bytes:
        """Generate realistic image file header"""
        ext = self._get_file_extension(filename)
        
        if ext == '.jpg' or ext == '.jpeg':
            # JPEG header
            return b'\xff\xd8\xff'
        elif ext == '.png':
            # PNG header
            return b'\x89PNG\r\n\x1a\n'
        elif ext == '.gif':
            # GIF header
            return b'GIF87a' if random.choice([True, False]) else b'GIF89a'
        elif ext == '.bmp':
            # BMP header
            return b'BM'
        else:
            # Generic image header
            return b'IMAGE' + b'\x00' * 27
    
    def _generate_document_header(self, filename: str) -> bytes:
        """Generate realistic document file header"""
        ext = self._get_file_extension(filename)
        
        if ext == '.pdf':
            # PDF header
            return b'%PDF-1.4\n'
        elif ext == '.doc' or ext == '.docx':
            # Word document header
            return b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
        elif ext == '.xls' or ext == '.xlsx':
            # Excel document header
            return b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
        elif ext == '.ppt' or ext == '.pptx':
            # PowerPoint document header
            return b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
        else:
            # Generic document header
            return b'DOCUMENT' + b'\x00' * 24
    
    def _generate_archive_header(self, filename: str) -> bytes:
        """Generate realistic archive file header"""
        ext = self._get_file_extension(filename)
        
        if ext == '.zip':
            # ZIP header
            return b'PK\x03\x04'
        elif ext == '.rar':
            # RAR header
            return b'Rar!\x1a\x07\x00'
        elif ext == '.7z':
            # 7-Zip header
            return b'7z\xbc\xaf\x27\x1c'
        elif ext == '.tar':
            # TAR header
            return b'\x75\x73\x74\x61\x72'
        else:
            # Generic archive header
            return b'ARCHIVE' + b'\x00' * 25
    
    def _generate_text_header(self, filename: str) -> bytes:
        """Generate realistic text file header"""
        ext = self._get_file_extension(filename)
        
        if ext == '.txt':
            # Plain text (no header)
            return b''
        elif ext == '.html' or ext == '.htm':
            # HTML header
            return b'<!DOCTYPE html>\n<html>\n<head>\n'
        elif ext == '.xml':
            # XML header
            return b'<?xml version="1.0" encoding="UTF-8"?>\n'
        elif ext == '.json':
            # JSON header
            return b'{\n'
        else:
            # Generic text header
            return b'TEXT' + b'\x00' * 28
    
    def _generate_realistic_file_content(self, filename: str, size: int) -> bytes:
        """Generate realistic file content based on file type"""
        ext = self._get_file_extension(filename)
        mime_type = self._get_mime_type(filename)
        
        # Generate appropriate header
        if mime_type.startswith('video/'):
            header = self._generate_video_header(filename)
        elif mime_type.startswith('audio/'):
            header = self._generate_audio_header(filename)
        elif mime_type.startswith('image/'):
            header = self._generate_image_header(filename)
        elif mime_type.startswith('application/pdf') or mime_type.startswith('application/msword'):
            header = self._generate_document_header(filename)
        elif mime_type.startswith('application/zip') or mime_type.startswith('application/x-rar'):
            header = self._generate_archive_header(filename)
        elif mime_type.startswith('text/'):
            header = self._generate_text_header(filename)
        else:
            # Generic binary header
            header = b'BINARY' + b'\x00' * 26
        
        # Calculate remaining size for content
        remaining_size = size - len(header)
        if remaining_size <= 0:
            return header[:size]
        
        # Generate realistic content based on file type
        if mime_type.startswith('text/'):
            # Text content
            content = self._generate_text_content(filename, remaining_size)
        else:
            # Binary content with some structure
            content = self._generate_binary_content(remaining_size)
        
        return header + content[:remaining_size]
    
    def _generate_text_content(self, filename: str, size: int) -> bytes:
        """Generate realistic text content"""
        ext = self._get_file_extension(filename)
        
        if ext == '.html' or ext == '.htm':
            content = f'''<title>Generated File</title>
</head>
<body>
<h1>Generated HTML File</h1>
<p>This is a generated HTML file for testing purposes.</p>
<p>File: {filename}</p>
<p>Size: {size} bytes</p>
</body>
</html>'''
        elif ext == '.xml':
            content = f'''<root>
    <title>Generated XML File</title>
    <description>This is a generated XML file for testing purposes.</description>
    <filename>{filename}</filename>
    <size>{size}</size>
</root>'''
        elif ext == '.json':
            content = f'''{{
    "title": "Generated JSON File",
    "description": "This is a generated JSON file for testing purposes",
    "filename": "{filename}",
    "size": {size}
}}'''
        else:
            # Plain text
            content = f'''Generated Text File
==================
This is a generated text file for testing purposes.

File: {filename}
Size: {size} bytes
Generated: {__import__('datetime').datetime.now().isoformat()}

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'''
        
        return content.encode('utf-8')
    
    def _generate_binary_content(self, size: int) -> bytes:
        """Generate realistic binary content"""
        # Generate some structured binary data
        content = bytearray()
        
        # Add some patterns to make it look realistic
        for i in range(0, size, 1024):
            chunk_size = min(1024, size - i)
            
            # Add some structure every 1KB
            if i % 4096 == 0:
                # Add a header-like structure
                content.extend(struct.pack('<I', chunk_size))
                content.extend(b'DATA' + b'\x00' * 4)
            
            # Generate semi-random data
            chunk = bytes(random.getrandbits(8) for _ in range(chunk_size))
            content.extend(chunk)
        
        return bytes(content)
    
    def write_files(self, download_folder: Path, files: List[Dict], total_size: int) -> bool:
        """Write downloaded files to disk with realistic content"""
        try:
            download_folder.mkdir(exist_ok=True)
            
            for file_info in files:
                file_path = download_folder / file_info['path']
                file_size = file_info['length']
                
                # Create parent directories
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Generate realistic file content
                content = self._generate_realistic_file_content(
                    file_info['path'], 
                    file_size
                )
                
                # Write file
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                self.logger.info(f"Wrote file: {file_path} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error writing files: {e}")
            return False
    
    def create_download_structure(self, download_folder: Path, files: List[Dict]) -> bool:
        """Create the folder structure for downloads"""
        try:
            download_folder.mkdir(exist_ok=True)
            
            for file_info in files:
                file_path = download_folder / file_info['path']
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating download structure: {e}")
            return False
    
    def cleanup_download_folder(self, download_folder: Path) -> bool:
        """Clean up download folder"""
        try:
            if download_folder.exists():
                import shutil
                shutil.rmtree(download_folder)
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up download folder: {e}")
            return False
    
    def get_file_info(self, file_path: Path) -> Dict[str, any]:
        """Get information about a file"""
        try:
            stat = file_path.stat()
            return {
                'name': file_path.name,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'is_file': file_path.is_file(),
                'is_dir': file_path.is_dir()
            }
        except Exception as e:
            self.logger.error(f"Error getting file info: {e}")
            return {}
    
    def list_download_files(self, download_folder: Path) -> List[Dict[str, any]]:
        """List all files in download folder"""
        try:
            files = []
            if download_folder.exists():
                for file_path in download_folder.rglob('*'):
                    if file_path.is_file():
                        files.append(self.get_file_info(file_path))
            return files
        except Exception as e:
            self.logger.error(f"Error listing download files: {e}")
            return [] 