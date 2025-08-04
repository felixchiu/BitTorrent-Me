"""
Design Patterns Implementation for Modern BitTorrent Client
Based on "Mastering Python Design Patterns: Craft essential Python patterns by following core design principles"

This module implements various design patterns to create a robust, maintainable, and extensible
BitTorrent client architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, Protocol
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager
import weakref

logger = logging.getLogger(__name__)

# ============================================================================
# 1. FACTORY PATTERN - Creates objects without specifying exact classes
# ============================================================================

class DownloadType(Enum):
    """Enumeration of download types"""
    SINGLE_FILE = "single_file"
    MULTI_FILE = "multi_file"
    STREAMING = "streaming"

class DownloadFactory:
    """Factory for creating different types of downloads"""
    
    _download_types: Dict[DownloadType, type] = {}
    
    @classmethod
    def register_download_type(cls, download_type: DownloadType, download_class: type) -> None:
        """Register a new download type"""
        cls._download_types[download_type] = download_class
    
    @classmethod
    def create_download(cls, download_type: DownloadType, **kwargs) -> 'Download':
        """Create a download instance based on type"""
        if download_type not in cls._download_types:
            raise ValueError(f"Unknown download type: {download_type}")
        
        download_class = cls._download_types[download_type]
        return download_class(**kwargs)

# ============================================================================
# 2. OBSERVER PATTERN - Notifies multiple objects about state changes
# ============================================================================

class DownloadObserver(Protocol):
    """Protocol for download observers"""
    def update(self, download_id: str, progress: float, speed: float) -> None:
        """Update observer with download progress"""
        ...

class DownloadSubject:
    """Subject that notifies observers about download state changes"""
    
    def __init__(self):
        self._observers: List[DownloadObserver] = []
        self._download_states: Dict[str, Dict[str, Any]] = {}
    
    def attach(self, observer: DownloadObserver) -> None:
        """Attach an observer"""
        self._observers.append(observer)
    
    def detach(self, observer: DownloadObserver) -> None:
        """Detach an observer"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify(self, download_id: str, progress: float, speed: float) -> None:
        """Notify all observers about state change"""
        self._download_states[download_id] = {
            'progress': progress,
            'speed': speed,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        for observer in self._observers:
            try:
                observer.update(download_id, progress, speed)
            except Exception as e:
                logger.error(f"Observer notification failed: {e}")

# ============================================================================
# 3. STRATEGY PATTERN - Encapsulates algorithms and makes them interchangeable
# ============================================================================

class DownloadStrategy(ABC):
    """Abstract base for download strategies"""
    
    @abstractmethod
    async def download(self, download: 'Download') -> bool:
        """Execute download strategy"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get strategy name"""
        pass

class SimulatedDownloadStrategy(DownloadStrategy):
    """Simulates BitTorrent download with realistic behavior"""
    
    async def download(self, download: 'Download') -> bool:
        """Simulate download process"""
        try:
            total_pieces = len(download.pieces)
            for i in range(total_pieces):
                if not download.downloading:
                    break
                
                # Simulate piece download
                await asyncio.sleep(0.01)
                download.downloaded_pieces.add(i)
                
                # Update progress
                progress = (i + 1) / total_pieces * 100
                download.download_progress = progress
                
            return True
        except Exception as e:
            logger.error(f"Simulated download failed: {e}")
            return False
    
    def get_name(self) -> str:
        return "simulated"

class RealDownloadStrategy(DownloadStrategy):
    """Real BitTorrent download implementation"""
    
    async def download(self, download: 'Download') -> bool:
        """Real BitTorrent download process"""
        # Implementation for actual BitTorrent protocol
        # This would include peer discovery, piece downloading, etc.
        logger.info("Real BitTorrent download not implemented yet")
        return False
    
    def get_name(self) -> str:
        return "real"

# ============================================================================
# 4. COMMAND PATTERN - Encapsulates requests as objects
# ============================================================================

class DownloadCommand(ABC):
    """Abstract command for download operations"""
    
    @abstractmethod
    async def execute(self) -> bool:
        """Execute the command"""
        pass
    
    @abstractmethod
    async def undo(self) -> bool:
        """Undo the command"""
        pass

class StartDownloadCommand(DownloadCommand):
    """Command to start a download"""
    
    def __init__(self, download: 'Download'):
        self.download = download
        self._previous_state: Optional[Dict[str, Any]] = None
    
    async def execute(self) -> bool:
        """Start the download"""
        self._previous_state = {
            'downloading': self.download.downloading,
            'paused': self.download.paused
        }
        
        self.download.downloading = True
        self.download.paused = False
        return True
    
    async def undo(self) -> bool:
        """Undo start command"""
        if self._previous_state:
            self.download.downloading = self._previous_state['downloading']
            self.download.paused = self._previous_state['paused']
        return True

class PauseDownloadCommand(DownloadCommand):
    """Command to pause a download"""
    
    def __init__(self, download: 'Download'):
        self.download = download
        self._was_downloading = False
    
    async def execute(self) -> bool:
        """Pause the download"""
        self._was_downloading = self.download.downloading
        self.download.paused = True
        return True
    
    async def undo(self) -> bool:
        """Undo pause command"""
        if self._was_downloading:
            self.download.paused = False
        return True

class StopDownloadCommand(DownloadCommand):
    """Command to stop a download"""
    
    def __init__(self, download: 'Download'):
        self.download = download
        self._previous_state: Optional[Dict[str, Any]] = None
    
    async def execute(self) -> bool:
        """Stop the download"""
        self._previous_state = {
            'downloading': self.download.downloading,
            'paused': self.download.paused,
            'progress': self.download.download_progress
        }
        
        self.download.downloading = False
        self.download.paused = False
        return True
    
    async def undo(self) -> bool:
        """Undo stop command"""
        if self._previous_state:
            self.download.downloading = self._previous_state['downloading']
            self.download.paused = self._previous_state['paused']
            self.download.download_progress = self._previous_state['progress']
        return True

# ============================================================================
# 5. SINGLETON PATTERN - Ensures only one instance exists
# ============================================================================

class BitTorrentClientSingleton:
    """Singleton BitTorrent client instance"""
    
    _instance: Optional['BitTorrentClientSingleton'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.downloads: Dict[str, 'Download'] = {}
            self._initialized = True

# ============================================================================
# 6. BUILDER PATTERN - Constructs complex objects step by step
# ============================================================================

@dataclass
class DownloadSettings:
    """Download configuration settings"""
    speed_limit: int = 0
    upload_limit: int = 0
    max_peers: int = 50
    max_connections: int = 100
    auto_stop: bool = True
    verify_pieces: bool = True
    pre_allocate: bool = True
    sequential_download: bool = False

class DownloadSettingsBuilder:
    """Builder for complex download settings"""
    
    def __init__(self):
        self.reset()
    
    def reset(self) -> None:
        """Reset builder to initial state"""
        self._settings = DownloadSettings()
    
    def with_speed_limit(self, limit: int) -> 'DownloadSettingsBuilder':
        """Set download speed limit"""
        self._settings.speed_limit = limit
        return self
    
    def with_upload_limit(self, limit: int) -> 'DownloadSettingsBuilder':
        """Set upload speed limit"""
        self._settings.upload_limit = limit
        return self
    
    def with_max_peers(self, max_peers: int) -> 'DownloadSettingsBuilder':
        """Set maximum peers"""
        self._settings.max_peers = max_peers
        return self
    
    def with_max_connections(self, max_connections: int) -> 'DownloadSettingsBuilder':
        """Set maximum connections"""
        self._settings.max_connections = max_connections
        return self
    
    def with_auto_stop(self, auto_stop: bool) -> 'DownloadSettingsBuilder':
        """Set auto-stop behavior"""
        self._settings.auto_stop = auto_stop
        return self
    
    def with_verify_pieces(self, verify: bool) -> 'DownloadSettingsBuilder':
        """Set piece verification"""
        self._settings.verify_pieces = verify
        return self
    
    def with_pre_allocate(self, pre_allocate: bool) -> 'DownloadSettingsBuilder':
        """Set pre-allocation behavior"""
        self._settings.pre_allocate = pre_allocate
        return self
    
    def with_sequential_download(self, sequential: bool) -> 'DownloadSettingsBuilder':
        """Set sequential download behavior"""
        self._settings.sequential_download = sequential
        return self
    
    def build(self) -> DownloadSettings:
        """Build and return the settings object"""
        settings = self._settings
        self.reset()
        return settings

# ============================================================================
# 7. STATE PATTERN - Allows object to alter behavior when state changes
# ============================================================================

class DownloadState(ABC):
    """Abstract download state"""
    
    @abstractmethod
    def start(self, download: 'Download') -> bool:
        """Start download from this state"""
        pass
    
    @abstractmethod
    def pause(self, download: 'Download') -> bool:
        """Pause download from this state"""
        pass
    
    @abstractmethod
    def resume(self, download: 'Download') -> bool:
        """Resume download from this state"""
        pass
    
    @abstractmethod
    def stop(self, download: 'Download') -> bool:
        """Stop download from this state"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get state name"""
        pass

class StoppedState(DownloadState):
    """Download is stopped"""
    
    def start(self, download: 'Download') -> bool:
        download.state = DownloadingState()
        download.downloading = True
        download.paused = False
        return True
    
    def pause(self, download: 'Download') -> bool:
        return False  # Cannot pause stopped download
    
    def resume(self, download: 'Download') -> bool:
        return False  # Cannot resume stopped download
    
    def stop(self, download: 'Download') -> bool:
        return False  # Already stopped
    
    def get_name(self) -> str:
        return "stopped"

class DownloadingState(DownloadState):
    """Download is active"""
    
    def start(self, download: 'Download') -> bool:
        return False  # Already started
    
    def pause(self, download: 'Download') -> bool:
        download.state = PausedState()
        download.paused = True
        return True
    
    def resume(self, download: 'Download') -> bool:
        return False  # Already downloading
    
    def stop(self, download: 'Download') -> bool:
        download.state = StoppedState()
        download.downloading = False
        download.paused = False
        return True
    
    def get_name(self) -> str:
        return "downloading"

class PausedState(DownloadState):
    """Download is paused"""
    
    def start(self, download: 'Download') -> bool:
        return False  # Cannot start paused download
    
    def pause(self, download: 'Download') -> bool:
        return False  # Already paused
    
    def resume(self, download: 'Download') -> bool:
        download.state = DownloadingState()
        download.paused = False
        return True
    
    def stop(self, download: 'Download') -> bool:
        download.state = StoppedState()
        download.downloading = False
        download.paused = False
        return True
    
    def get_name(self) -> str:
        return "paused"

class CompletedState(DownloadState):
    """Download is completed"""
    
    def start(self, download: 'Download') -> bool:
        return False  # Cannot restart completed download
    
    def pause(self, download: 'Download') -> bool:
        return False  # Cannot pause completed download
    
    def resume(self, download: 'Download') -> bool:
        return False  # Cannot resume completed download
    
    def stop(self, download: 'Download') -> bool:
        return False  # Cannot stop completed download
    
    def get_name(self) -> str:
        return "completed"

# ============================================================================
# 8. TEMPLATE METHOD PATTERN - Defines algorithm skeleton
# ============================================================================

class DownloadTemplate(ABC):
    """Template method for download process"""
    
    def __init__(self, download: 'Download'):
        self.download = download
    
    async def execute_download(self) -> bool:
        """Template method for download execution"""
        try:
            # Hook method - can be overridden
            await self.pre_download()
            
            # Core download logic
            success = await self.download_pieces()
            
            # Hook method - can be overridden
            await self.post_download(success)
            
            return success
        except Exception as e:
            logger.error(f"Download template execution failed: {e}")
            await self.handle_error(e)
            return False
    
    @abstractmethod
    async def download_pieces(self) -> bool:
        """Download pieces - must be implemented by subclasses"""
        pass
    
    async def pre_download(self) -> None:
        """Pre-download hook - can be overridden"""
        logger.info(f"Starting download: {self.download.name}")
    
    async def post_download(self, success: bool) -> None:
        """Post-download hook - can be overridden"""
        if success:
            logger.info(f"Download completed: {self.download.name}")
        else:
            logger.error(f"Download failed: {self.download.name}")
    
    async def handle_error(self, error: Exception) -> None:
        """Error handling hook - can be overridden"""
        logger.error(f"Download error: {error}")

class SimulatedDownloadTemplate(DownloadTemplate):
    """Simulated download template implementation"""
    
    async def download_pieces(self) -> bool:
        """Simulate piece downloading"""
        total_pieces = len(self.download.pieces)
        
        for i in range(total_pieces):
            if not self.download.downloading:
                break
            
            # Simulate piece download
            await asyncio.sleep(0.01)
            self.download.downloaded_pieces.add(i)
            
            # Update progress
            progress = (i + 1) / total_pieces * 100
            self.download.download_progress = progress
        
        return len(self.download.downloaded_pieces) == total_pieces

# ============================================================================
# 9. DECORATOR PATTERN - Adds behavior without altering structure
# ============================================================================

class DownloadDecorator(ABC):
    """Abstract decorator for download functionality"""
    
    def __init__(self, download: 'Download'):
        self.download = download
    
    @abstractmethod
    async def start_download(self) -> bool:
        """Start download with decoration"""
        pass

class SpeedLimitDecorator(DownloadDecorator):
    """Decorator to add speed limiting to downloads"""
    
    def __init__(self, download: 'Download', speed_limit: int):
        super().__init__(download)
        self.speed_limit = speed_limit
    
    async def start_download(self) -> bool:
        """Start download with speed limiting"""
        logger.info(f"Starting download with speed limit: {self.speed_limit} KB/s")
        
        # Apply speed limiting logic
        if self.speed_limit > 0:
            # Calculate delay based on speed limit
            delay = 1.0 / (self.speed_limit / 1024)  # Convert to seconds
            await asyncio.sleep(delay)
        
        return await self.download.start_download()

class ProgressTrackingDecorator(DownloadDecorator):
    """Decorator to add progress tracking to downloads"""
    
    def __init__(self, download: 'Download', observer: DownloadObserver):
        super().__init__(download)
        self.observer = observer
    
    async def start_download(self) -> bool:
        """Start download with progress tracking"""
        logger.info("Starting download with progress tracking")
        
        # Start progress tracking
        asyncio.create_task(self._track_progress())
        
        return await self.download.start_download()
    
    async def _track_progress(self) -> None:
        """Track download progress"""
        while self.download.downloading:
            progress = self.download.download_progress
            speed = self.download.download_speed
            
            # Notify observer
            self.observer.update(self.download.torrent_id, progress, speed)
            
            await asyncio.sleep(1)  # Update every second

# ============================================================================
# 10. CHAIN OF RESPONSIBILITY PATTERN - Passes requests along handler chain
# ============================================================================

class DownloadHandler(ABC):
    """Abstract handler in the chain of responsibility"""
    
    def __init__(self):
        self._next_handler: Optional[DownloadHandler] = None
    
    def set_next(self, handler: 'DownloadHandler') -> 'DownloadHandler':
        """Set next handler in chain"""
        self._next_handler = handler
        return handler
    
    @abstractmethod
    async def handle(self, download: 'Download') -> bool:
        """Handle the download request"""
        pass
    
    async def _handle_next(self, download: 'Download') -> bool:
        """Pass to next handler if exists"""
        if self._next_handler:
            return await self._next_handler.handle(download)
        return True

class ValidationHandler(DownloadHandler):
    """Handler for download validation"""
    
    async def handle(self, download: 'Download') -> bool:
        """Validate download before processing"""
        logger.info(f"Validating download: {download.name}")
        
        # Validate download parameters
        if not download.pieces:
            logger.error("No pieces found in download")
            return False
        
        if download.total_size <= 0:
            logger.error("Invalid total size")
            return False
        
        # Pass to next handler
        return await self._handle_next(download)

class ResourceCheckHandler(DownloadHandler):
    """Handler for resource availability check"""
    
    async def handle(self, download: 'Download') -> bool:
        """Check resource availability"""
        logger.info(f"Checking resources for: {download.name}")
        
        # Check disk space
        import shutil
        total, used, free = shutil.disk_usage(download.download_dir)
        required_space = download.total_size
        
        if free < required_space:
            logger.error(f"Insufficient disk space: {free} < {required_space}")
            return False
        
        # Pass to next handler
        return await self._handle_next(download)

class ExecutionHandler(DownloadHandler):
    """Handler for actual download execution"""
    
    async def handle(self, download: 'Download') -> bool:
        """Execute the download"""
        logger.info(f"Executing download: {download.name}")
        
        # Start the download
        return await download.start_download()

# ============================================================================
# 11. MEDIATOR PATTERN - Centralizes complex communications
# ============================================================================

class DownloadMediator:
    """Mediator for coordinating download operations"""
    
    def __init__(self):
        self.downloads: Dict[str, 'Download'] = {}
        self.observers: List[DownloadObserver] = []
        self.handlers: List[DownloadHandler] = []
    
    def register_download(self, download: 'Download') -> None:
        """Register a download with the mediator"""
        self.downloads[download.torrent_id] = download
        logger.info(f"Registered download: {download.torrent_id}")
    
    def register_observer(self, observer: DownloadObserver) -> None:
        """Register an observer with the mediator"""
        self.observers.append(observer)
        logger.info("Registered observer")
    
    def register_handler(self, handler: DownloadHandler) -> None:
        """Register a handler with the mediator"""
        self.handlers.append(handler)
        logger.info("Registered handler")
    
    async def start_download(self, torrent_id: str) -> bool:
        """Start download through mediator"""
        if torrent_id not in self.downloads:
            logger.error(f"Download not found: {torrent_id}")
            return False
        
        download = self.downloads[torrent_id]
        
        # Create handler chain
        chain = self._create_handler_chain()
        
        # Execute through chain
        success = await chain.handle(download)
        
        if success:
            # Notify observers
            for observer in self.observers:
                observer.update(torrent_id, 0.0, 0.0)
        
        return success
    
    def _create_handler_chain(self) -> DownloadHandler:
        """Create handler chain"""
        if not self.handlers:
            return ExecutionHandler()
        
        # Build chain
        chain = self.handlers[0]
        current = chain
        
        for handler in self.handlers[1:]:
            current.set_next(handler)
            current = handler
        
        return chain

# ============================================================================
# 12. MEMENTO PATTERN - Captures and restores object state
# ============================================================================

@dataclass
class DownloadMemento:
    """Memento for storing download state"""
    torrent_id: str
    name: str
    progress: float
    downloaded_pieces: set
    settings: DownloadSettings
    timestamp: float

class DownloadCaretaker:
    """Caretaker for managing download mementos"""
    
    def __init__(self):
        self._mementos: Dict[str, DownloadMemento] = {}
    
    def save_state(self, download: 'Download') -> None:
        """Save download state"""
        memento = DownloadMemento(
            torrent_id=download.torrent_id,
            name=download.name,
            progress=download.download_progress,
            downloaded_pieces=download.downloaded_pieces.copy(),
            settings=download.settings,
            timestamp=asyncio.get_event_loop().time()
        )
        self._mementos[download.torrent_id] = memento
        logger.info(f"Saved state for: {download.torrent_id}")
    
    def restore_state(self, download: 'Download') -> bool:
        """Restore download state"""
        if download.torrent_id not in self._mementos:
            return False
        
        memento = self._mementos[download.torrent_id]
        download.download_progress = memento.progress
        download.downloaded_pieces = memento.downloaded_pieces.copy()
        download.settings = memento.settings
        
        logger.info(f"Restored state for: {download.torrent_id}")
        return True
    
    def get_memento(self, torrent_id: str) -> Optional[DownloadMemento]:
        """Get memento for specific download"""
        return self._mementos.get(torrent_id)

# ============================================================================
# 13. VISITOR PATTERN - Separates algorithms from object structure
# ============================================================================

class DownloadVisitor(ABC):
    """Abstract visitor for download operations"""
    
    @abstractmethod
    def visit_single_file_download(self, download: 'Download') -> None:
        """Visit single file download"""
        pass
    
    @abstractmethod
    def visit_multi_file_download(self, download: 'Download') -> None:
        """Visit multi file download"""
        pass

class ProgressVisitor(DownloadVisitor):
    """Visitor for progress calculation"""
    
    def visit_single_file_download(self, download: 'Download') -> None:
        """Calculate progress for single file download"""
        total_pieces = len(download.pieces)
        downloaded_pieces = len(download.downloaded_pieces)
        download.download_progress = (downloaded_pieces / total_pieces) * 100 if total_pieces > 0 else 0
    
    def visit_multi_file_download(self, download: 'Download') -> None:
        """Calculate progress for multi file download"""
        total_size = sum(file.length for file in download.files if file.selected)
        downloaded_size = sum(file.length for file in download.files if file.selected and file.downloaded)
        download.download_progress = (downloaded_size / total_size) * 100 if total_size > 0 else 0

class ValidationVisitor(DownloadVisitor):
    """Visitor for download validation"""
    
    def visit_single_file_download(self, download: 'Download') -> None:
        """Validate single file download"""
        if not download.name:
            raise ValueError("Download name is required")
        if download.total_size <= 0:
            raise ValueError("Invalid total size")
    
    def visit_multi_file_download(self, download: 'Download') -> None:
        """Validate multi file download"""
        if not download.files:
            raise ValueError("No files in multi-file download")
        if not any(file.selected for file in download.files):
            raise ValueError("No files selected for download")

# ============================================================================
# 14. INTERPRETER PATTERN - Defines grammar and interpretation
# ============================================================================

class DownloadExpression(ABC):
    """Abstract expression for download operations"""
    
    @abstractmethod
    def interpret(self, context: Dict[str, Any]) -> bool:
        """Interpret the expression"""
        pass

class StartExpression(DownloadExpression):
    """Expression for starting downloads"""
    
    def interpret(self, context: Dict[str, Any]) -> bool:
        """Interpret start expression"""
        download = context.get('download')
        if not download:
            return False
        
        return download.downloading and not download.paused

class PauseExpression(DownloadExpression):
    """Expression for pausing downloads"""
    
    def interpret(self, context: Dict[str, Any]) -> bool:
        """Interpret pause expression"""
        download = context.get('download')
        if not download:
            return False
        
        return download.downloading and download.paused

class CompleteExpression(DownloadExpression):
    """Expression for completed downloads"""
    
    def interpret(self, context: Dict[str, Any]) -> bool:
        """Interpret complete expression"""
        download = context.get('download')
        if not download:
            return False
        
        return download.completed

class AndExpression(DownloadExpression):
    """Expression for logical AND"""
    
    def __init__(self, left: DownloadExpression, right: DownloadExpression):
        self.left = left
        self.right = right
    
    def interpret(self, context: Dict[str, Any]) -> bool:
        """Interpret AND expression"""
        return self.left.interpret(context) and self.right.interpret(context)

class OrExpression(DownloadExpression):
    """Expression for logical OR"""
    
    def __init__(self, left: DownloadExpression, right: DownloadExpression):
        self.left = left
        self.right = right
    
    def interpret(self, context: Dict[str, Any]) -> bool:
        """Interpret OR expression"""
        return self.left.interpret(context) or self.right.interpret(context)

# ============================================================================
# 15. ITERATOR PATTERN - Accesses elements without exposing structure
# ============================================================================

class DownloadIterator(ABC):
    """Abstract iterator for downloads"""
    
    @abstractmethod
    def has_next(self) -> bool:
        """Check if there are more elements"""
        pass
    
    @abstractmethod
    def next(self) -> 'Download':
        """Get next element"""
        pass

class DownloadCollection:
    """Collection of downloads with iterator support"""
    
    def __init__(self):
        self.downloads: List['Download'] = []
    
    def add_download(self, download: 'Download') -> None:
        """Add download to collection"""
        self.downloads.append(download)
    
    def create_iterator(self) -> DownloadIterator:
        """Create iterator for downloads"""
        return DownloadListIterator(self.downloads)

class DownloadListIterator(DownloadIterator):
    """Iterator for list of downloads"""
    
    def __init__(self, downloads: List['Download']):
        self.downloads = downloads
        self.index = 0
    
    def has_next(self) -> bool:
        """Check if there are more downloads"""
        return self.index < len(self.downloads)
    
    def next(self) -> 'Download':
        """Get next download"""
        if not self.has_next():
            raise StopIteration()
        
        download = self.downloads[self.index]
        self.index += 1
        return download

# ============================================================================
# 16. PROTOTYPE PATTERN - Creates new objects by cloning existing ones
# ============================================================================

class DownloadPrototype(ABC):
    """Abstract prototype for downloads"""
    
    @abstractmethod
    def clone(self) -> 'DownloadPrototype':
        """Clone the prototype"""
        pass

class Download(DownloadPrototype):
    """Download class with prototype support"""
    
    def __init__(self, torrent_id: str, name: str, total_size: int, settings: DownloadSettings):
        self.torrent_id = torrent_id
        self.name = name
        self.total_size = total_size
        self.settings = settings
        self.downloading = False
        self.paused = False
        self.completed = False
        self.download_progress = 0.0
        self.download_speed = 0.0
        self.downloaded_pieces: set = set()
        self.pieces: List = []
        self.files: List = []
        self.state: DownloadState = StoppedState()
    
    def clone(self) -> 'Download':
        """Clone the download"""
        cloned = Download(
            torrent_id=f"{self.torrent_id}_clone",
            name=f"{self.name} (Clone)",
            total_size=self.total_size,
            settings=self.settings
        )
        
        # Copy state
        cloned.downloading = self.downloading
        cloned.paused = self.paused
        cloned.completed = self.completed
        cloned.download_progress = self.download_progress
        cloned.download_speed = self.download_speed
        cloned.downloaded_pieces = self.downloaded_pieces.copy()
        cloned.pieces = self.pieces.copy()
        cloned.files = self.files.copy()
        
        return cloned
    
    async def start_download(self) -> bool:
        """Start the download"""
        return self.state.start(self)
    
    async def pause_download(self) -> bool:
        """Pause the download"""
        return self.state.pause(self)
    
    async def resume_download(self) -> bool:
        """Resume the download"""
        return self.state.resume(self)
    
    async def stop_download(self) -> bool:
        """Stop the download"""
        return self.state.stop(self)

# ============================================================================
# 17. ADAPTER PATTERN - Allows incompatible interfaces to work together
# ============================================================================

class LegacyDownloadSystem:
    """Legacy download system with old interface"""
    
    def start_legacy_download(self, torrent_file: str, output_dir: str) -> bool:
        """Legacy download method"""
        logger.info(f"Legacy download: {torrent_file} -> {output_dir}")
        return True

class DownloadAdapter:
    """Adapter to make legacy system work with new interface"""
    
    def __init__(self, legacy_system: LegacyDownloadSystem):
        self.legacy_system = legacy_system
    
    async def start_download(self, download: Download) -> bool:
        """Adapt legacy method to new interface"""
        torrent_file = f"{download.torrent_id}.torrent"
        output_dir = str(download.download_dir)
        
        return self.legacy_system.start_legacy_download(torrent_file, output_dir)

# ============================================================================
# 18. BRIDGE PATTERN - Separates abstraction from implementation
# ============================================================================

class DownloadImplementation(ABC):
    """Abstract implementation for download operations"""
    
    @abstractmethod
    async def download_piece(self, piece_index: int) -> bool:
        """Download a specific piece"""
        pass
    
    @abstractmethod
    async def verify_piece(self, piece_index: int) -> bool:
        """Verify a specific piece"""
        pass

class SimulatedDownloadImplementation(DownloadImplementation):
    """Simulated implementation of download operations"""
    
    async def download_piece(self, piece_index: int) -> bool:
        """Simulate piece download"""
        await asyncio.sleep(0.01)  # Simulate download time
        return True
    
    async def verify_piece(self, piece_index: int) -> bool:
        """Simulate piece verification"""
        return True

class RealDownloadImplementation(DownloadImplementation):
    """Real implementation of download operations"""
    
    async def download_piece(self, piece_index: int) -> bool:
        """Real piece download implementation"""
        # Real BitTorrent implementation would go here
        logger.info(f"Downloading piece {piece_index}")
        return True
    
    async def verify_piece(self, piece_index: int) -> bool:
        """Real piece verification implementation"""
        # Real verification implementation would go here
        logger.info(f"Verifying piece {piece_index}")
        return True

class DownloadAbstraction:
    """Abstraction for download operations"""
    
    def __init__(self, implementation: DownloadImplementation):
        self.implementation = implementation
    
    async def download_piece(self, piece_index: int) -> bool:
        """Download piece using implementation"""
        return await self.implementation.download_piece(piece_index)
    
    async def verify_piece(self, piece_index: int) -> bool:
        """Verify piece using implementation"""
        return await self.implementation.verify_piece(piece_index)

# ============================================================================
# 19. COMPOSITE PATTERN - Treats individual and composite objects uniformly
# ============================================================================

class DownloadComponent(ABC):
    """Abstract component for download hierarchy"""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get component name"""
        pass
    
    @abstractmethod
    def get_size(self) -> int:
        """Get component size"""
        pass
    
    @abstractmethod
    def get_progress(self) -> float:
        """Get component progress"""
        pass

class DownloadFile(DownloadComponent):
    """Leaf component representing a file"""
    
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size
        self.downloaded = False
    
    def get_name(self) -> str:
        return self.name
    
    def get_size(self) -> int:
        return self.size
    
    def get_progress(self) -> float:
        return 100.0 if self.downloaded else 0.0

class DownloadFolder(DownloadComponent):
    """Composite component representing a folder"""
    
    def __init__(self, name: str):
        self.name = name
        self.children: List[DownloadComponent] = []
    
    def add(self, component: DownloadComponent) -> None:
        """Add child component"""
        self.children.append(component)
    
    def remove(self, component: DownloadComponent) -> None:
        """Remove child component"""
        if component in self.children:
            self.children.remove(component)
    
    def get_name(self) -> str:
        return self.name
    
    def get_size(self) -> int:
        return sum(child.get_size() for child in self.children)
    
    def get_progress(self) -> float:
        if not self.children:
            return 0.0
        
        total_progress = sum(child.get_progress() for child in self.children)
        return total_progress / len(self.children)

# ============================================================================
# 20. FLYWEIGHT PATTERN - Reduces memory usage by sharing common data
# ============================================================================

class PieceFlyweight:
    """Flyweight for piece data to reduce memory usage"""
    
    def __init__(self):
        self._piece_data: Dict[int, bytes] = {}
    
    def get_piece_data(self, piece_hash: int) -> bytes:
        """Get piece data, creating if necessary"""
        if piece_hash not in self._piece_data:
            # Generate piece data (in real implementation, this would be downloaded)
            self._piece_data[piece_hash] = os.urandom(16384)  # 16KB pieces
        
        return self._piece_data[piece_hash]
    
    def clear_cache(self) -> None:
        """Clear cached piece data"""
        self._piece_data.clear()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_download_with_patterns(torrent_id: str, name: str, total_size: int, 
                                settings: DownloadSettings) -> Download:
    """Create a download using multiple design patterns"""
    
    # Create download using factory pattern
    download = Download(torrent_id, name, total_size, settings)
    
    # Apply decorators
    download = SpeedLimitDecorator(download, settings.speed_limit)
    download = ProgressTrackingDecorator(download, DownloadSubject())
    
    # Register with mediator
    mediator = DownloadMediator()
    mediator.register_download(download)
    
    return download

def setup_handler_chain() -> DownloadHandler:
    """Setup chain of responsibility for download processing"""
    
    validation_handler = ValidationHandler()
    resource_handler = ResourceCheckHandler()
    execution_handler = ExecutionHandler()
    
    # Build chain
    validation_handler.set_next(resource_handler)
    resource_handler.set_next(execution_handler)
    
    return validation_handler

def create_settings_builder() -> DownloadSettingsBuilder:
    """Create settings using builder pattern"""
    
    return (DownloadSettingsBuilder()
            .with_speed_limit(1024)
            .with_upload_limit(512)
            .with_max_peers(50)
            .with_max_connections(100)
            .with_auto_stop(True)
            .with_verify_pieces(True)
            .with_pre_allocate(True))

# ============================================================================
# REGISTRATION OF PATTERNS
# ============================================================================

# Register download types with factory
DownloadFactory.register_download_type(DownloadType.SINGLE_FILE, Download)
DownloadFactory.register_download_type(DownloadType.MULTI_FILE, Download)

# Import os for flyweight pattern
import os 