"""
Comprehensive Test Suite for Design Patterns Implementation
Tests all design patterns from "Mastering Python Design Patterns"
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import design patterns
from design_patterns import (
    # Factory Pattern
    DownloadFactory, DownloadType,
    
    # Observer Pattern
    DownloadSubject, DownloadObserver,
    
    # Strategy Pattern
    DownloadStrategy, SimulatedDownloadStrategy, RealDownloadStrategy,
    
    # Command Pattern
    DownloadCommand, StartDownloadCommand, PauseDownloadCommand, StopDownloadCommand,
    
    # Singleton Pattern
    BitTorrentClientSingleton,
    
    # Builder Pattern
    DownloadSettingsBuilder, DownloadSettings,
    
    # State Pattern
    DownloadState, StoppedState, DownloadingState, PausedState, CompletedState,
    
    # Template Method Pattern
    DownloadTemplate, SimulatedDownloadTemplate,
    
    # Decorator Pattern
    DownloadDecorator, SpeedLimitDecorator, ProgressTrackingDecorator,
    
    # Chain of Responsibility Pattern
    DownloadHandler, ValidationHandler, ResourceCheckHandler, ExecutionHandler,
    
    # Mediator Pattern
    DownloadMediator,
    
    # Memento Pattern
    DownloadMemento, DownloadCaretaker,
    
    # Visitor Pattern
    DownloadVisitor, ProgressVisitor, ValidationVisitor,
    
    # Interpreter Pattern
    DownloadExpression, StartExpression, PauseExpression, CompleteExpression,
    AndExpression, OrExpression,
    
    # Iterator Pattern
    DownloadIterator, DownloadCollection, DownloadListIterator,
    
    # Prototype Pattern
    DownloadPrototype, Download,
    
    # Adapter Pattern
    LegacyDownloadSystem, DownloadAdapter,
    
    # Bridge Pattern
    DownloadImplementation, SimulatedDownloadImplementation, RealDownloadImplementation,
    DownloadAbstraction,
    
    # Composite Pattern
    DownloadComponent, DownloadFile, DownloadFolder,
    
    # Flyweight Pattern
    PieceFlyweight,
    
    # Utility functions
    create_download_with_patterns, setup_handler_chain, create_settings_builder
)

# ============================================================================
# FACTORY PATTERN TESTS
# ============================================================================

class TestFactoryPattern:
    """Test Factory Pattern implementation"""
    
    def test_factory_registration(self):
        """Test registering download types with factory"""
        # Clear existing registrations
        DownloadFactory._download_types.clear()
        
        # Register download types
        DownloadFactory.register_download_type(DownloadType.SINGLE_FILE, Download)
        DownloadFactory.register_download_type(DownloadType.MULTI_FILE, Download)
        
        assert DownloadType.SINGLE_FILE in DownloadFactory._download_types
        assert DownloadType.MULTI_FILE in DownloadFactory._download_types
    
    def test_factory_creation(self):
        """Test creating downloads through factory"""
        # Register types
        DownloadFactory.register_download_type(DownloadType.SINGLE_FILE, Download)
        
        # Create download
        settings = DownloadSettings()
        download = DownloadFactory.create_download(
            DownloadType.SINGLE_FILE,
            torrent_id="test123",
            name="test.torrent",
            total_size=1024,
            settings=settings
        )
        
        assert isinstance(download, Download)
        assert download.torrent_id == "test123"
        assert download.name == "test.torrent"
        assert download.total_size == 1024
    
    def test_factory_unknown_type(self):
        """Test factory with unknown download type"""
        with pytest.raises(ValueError, match="Unknown download type"):
            DownloadFactory.create_download(DownloadType.STREAMING)

# ============================================================================
# OBSERVER PATTERN TESTS
# ============================================================================

class TestObserverPattern:
    """Test Observer Pattern implementation"""
    
    def test_observer_attachment(self):
        """Test attaching and detaching observers"""
        subject = DownloadSubject()
        observer = Mock(spec=DownloadObserver)
        
        # Attach observer
        subject.attach(observer)
        assert observer in subject._observers
        
        # Detach observer
        subject.detach(observer)
        assert observer not in subject._observers
    
    def test_observer_notification(self):
        """Test notifying observers about state changes"""
        subject = DownloadSubject()
        observer = Mock(spec=DownloadObserver)
        subject.attach(observer)
        
        # Notify observers
        subject.notify("test123", 50.0, 1024.0)
        
        # Verify observer was called
        observer.update.assert_called_once_with("test123", 50.0, 1024.0)
        
        # Verify state was stored
        assert "test123" in subject._download_states
        assert subject._download_states["test123"]["progress"] == 50.0
        assert subject._download_states["test123"]["speed"] == 1024.0
    
    def test_observer_error_handling(self):
        """Test error handling in observer notifications"""
        subject = DownloadSubject()
        observer = Mock(spec=DownloadObserver)
        observer.update.side_effect = Exception("Observer error")
        subject.attach(observer)
        
        # Should not raise exception
        subject.notify("test123", 50.0, 1024.0)
        
        # Observer should still be called
        observer.update.assert_called_once()

# ============================================================================
# STRATEGY PATTERN TESTS
# ============================================================================

class TestStrategyPattern:
    """Test Strategy Pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_simulated_download_strategy(self):
        """Test simulated download strategy"""
        strategy = SimulatedDownloadStrategy()
        
        # Create mock download
        download = Mock()
        download.pieces = [Mock() for _ in range(5)]
        download.downloading = True
        download.downloaded_pieces = set()
        download.download_progress = 0.0
        
        # Execute strategy
        result = await strategy.download(download)
        
        assert result is True
        assert len(download.downloaded_pieces) == 5
        assert download.download_progress == 100.0
    
    @pytest.mark.asyncio
    async def test_real_download_strategy(self):
        """Test real download strategy (not implemented)"""
        strategy = RealDownloadStrategy()
        
        download = Mock()
        result = await strategy.download(download)
        
        assert result is False  # Not implemented yet
    
    def test_strategy_names(self):
        """Test strategy names"""
        simulated = SimulatedDownloadStrategy()
        real = RealDownloadStrategy()
        
        assert simulated.get_name() == "simulated"
        assert real.get_name() == "real"

# ============================================================================
# COMMAND PATTERN TESTS
# ============================================================================

class TestCommandPattern:
    """Test Command Pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_start_command(self):
        """Test start download command"""
        download = Mock()
        download.downloading = False
        download.paused = False
        
        command = StartDownloadCommand(download)
        
        # Execute command
        result = await command.execute()
        assert result is True
        assert download.downloading is True
        assert download.paused is False
        
        # Undo command
        result = await command.undo()
        assert result is True
        assert download.downloading is False
        assert download.paused is False
    
    @pytest.mark.asyncio
    async def test_pause_command(self):
        """Test pause download command"""
        download = Mock()
        download.downloading = True
        download.paused = False
        
        command = PauseDownloadCommand(download)
        
        # Execute command
        result = await command.execute()
        assert result is True
        assert download.paused is True
        
        # Undo command
        result = await command.undo()
        assert result is True
        assert download.paused is False
    
    @pytest.mark.asyncio
    async def test_stop_command(self):
        """Test stop download command"""
        download = Mock()
        download.downloading = True
        download.paused = False
        download.download_progress = 50.0
        
        command = StopDownloadCommand(download)
        
        # Execute command
        result = await command.execute()
        assert result is True
        assert download.downloading is False
        assert download.paused is False
        
        # Undo command
        result = await command.undo()
        assert result is True
        assert download.downloading is True
        assert download.paused is False
        assert download.download_progress == 50.0

# ============================================================================
# SINGLETON PATTERN TESTS
# ============================================================================

class TestSingletonPattern:
    """Test Singleton Pattern implementation"""
    
    def test_singleton_creation(self):
        """Test singleton instance creation"""
        # Clear singleton instance
        BitTorrentClientSingleton._instance = None
        
        # Create first instance
        instance1 = BitTorrentClientSingleton()
        assert instance1 is not None
        
        # Create second instance (should be the same)
        instance2 = BitTorrentClientSingleton()
        assert instance2 is instance1
    
    def test_singleton_initialization(self):
        """Test singleton initialization"""
        # Clear singleton instance
        BitTorrentClientSingleton._instance = None
        
        instance = BitTorrentClientSingleton()
        assert hasattr(instance, 'downloads')
        assert isinstance(instance.downloads, dict)

# ============================================================================
# BUILDER PATTERN TESTS
# ============================================================================

class TestBuilderPattern:
    """Test Builder Pattern implementation"""
    
    def test_settings_builder(self):
        """Test building download settings"""
        settings = (DownloadSettingsBuilder()
                   .with_speed_limit(1024)
                   .with_upload_limit(512)
                   .with_max_peers(50)
                   .with_max_connections(100)
                   .with_auto_stop(True)
                   .with_verify_pieces(True)
                   .with_pre_allocate(True)
                   .with_sequential_download(False)
                   .build())
        
        assert settings.speed_limit == 1024
        assert settings.upload_limit == 512
        assert settings.max_peers == 50
        assert settings.max_connections == 100
        assert settings.auto_stop is True
        assert settings.verify_pieces is True
        assert settings.pre_allocate is True
        assert settings.sequential_download is False
    
    def test_builder_reset(self):
        """Test builder reset functionality"""
        builder = DownloadSettingsBuilder()
        
        # Build first settings
        settings1 = builder.with_speed_limit(1024).build()
        assert settings1.speed_limit == 1024
        
        # Build second settings (should be reset)
        settings2 = builder.with_upload_limit(512).build()
        assert settings2.speed_limit == 0  # Reset
        assert settings2.upload_limit == 512

# ============================================================================
# STATE PATTERN TESTS
# ============================================================================

class TestStatePattern:
    """Test State Pattern implementation"""
    
    def test_stopped_state(self):
        """Test stopped state behavior"""
        download = Mock()
        download.downloading = False
        download.paused = False
        
        state = StoppedState()
        
        # Test start from stopped
        result = state.start(download)
        assert result is True
        assert download.downloading is True
        assert download.paused is False
        
        # Test pause from stopped (should fail)
        result = state.pause(download)
        assert result is False
    
    def test_downloading_state(self):
        """Test downloading state behavior"""
        download = Mock()
        download.downloading = True
        download.paused = False
        
        state = DownloadingState()
        
        # Test pause from downloading
        result = state.pause(download)
        assert result is True
        assert download.paused is True
        
        # Test stop from downloading
        result = state.stop(download)
        assert result is True
        assert download.downloading is False
        assert download.paused is False
    
    def test_paused_state(self):
        """Test paused state behavior"""
        download = Mock()
        download.downloading = True
        download.paused = True
        
        state = PausedState()
        
        # Test resume from paused
        result = state.resume(download)
        assert result is True
        assert download.paused is False
    
    def test_completed_state(self):
        """Test completed state behavior"""
        download = Mock()
        download.completed = True
        
        state = CompletedState()
        
        # All operations should fail for completed state
        assert state.start(download) is False
        assert state.pause(download) is False
        assert state.resume(download) is False
        assert state.stop(download) is False

# ============================================================================
# TEMPLATE METHOD PATTERN TESTS
# ============================================================================

class TestTemplateMethodPattern:
    """Test Template Method Pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_simulated_download_template(self):
        """Test simulated download template"""
        download = Mock()
        download.name = "test.torrent"
        download.downloading = True
        download.pieces = [Mock() for _ in range(3)]
        download.downloaded_pieces = set()
        download.download_progress = 0.0
        
        template = SimulatedDownloadTemplate(download)
        
        # Execute template
        result = await template.execute_download()
        
        assert result is True
        assert len(download.downloaded_pieces) == 3
        assert download.download_progress == 100.0
    
    @pytest.mark.asyncio
    async def test_template_error_handling(self):
        """Test template error handling"""
        download = Mock()
        download.name = "test.torrent"
        download.downloading = True
        download.pieces = [Mock()]
        download.downloaded_pieces = set()
        
        template = SimulatedDownloadTemplate(download)
        
        # Mock error in download_pieces
        with patch.object(template, 'download_pieces', side_effect=Exception("Test error")):
            result = await template.execute_download()
            assert result is False

# ============================================================================
# DECORATOR PATTERN TESTS
# ============================================================================

class TestDecoratorPattern:
    """Test Decorator Pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_speed_limit_decorator(self):
        """Test speed limit decorator"""
        download = Mock()
        download.start_download = AsyncMock(return_value=True)
        
        decorator = SpeedLimitDecorator(download, 1024)
        
        # Test with speed limit
        result = await decorator.start_download()
        assert result is True
        download.start_download.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_progress_tracking_decorator(self):
        """Test progress tracking decorator"""
        download = Mock()
        download.torrent_id = "test123"
        download.downloading = True
        download.download_progress = 50.0
        download.download_speed = 1024.0
        download.start_download = AsyncMock(return_value=True)
        
        observer = Mock()
        decorator = ProgressTrackingDecorator(download, observer)
        
        # Start download
        result = await decorator.start_download()
        assert result is True
        
        # Wait a bit for progress tracking
        await asyncio.sleep(0.1)
        
        # Verify observer was called
        assert observer.update.called

# ============================================================================
# CHAIN OF RESPONSIBILITY PATTERN TESTS
# ============================================================================

class TestChainOfResponsibilityPattern:
    """Test Chain of Responsibility Pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_validation_handler(self):
        """Test validation handler"""
        handler = ValidationHandler()
        
        # Valid download
        download = Mock()
        download.name = "test.torrent"
        download.pieces = [Mock()]
        download.total_size = 1024
        
        result = await handler.handle(download)
        assert result is True
        
        # Invalid download (no pieces)
        download.pieces = []
        result = await handler.handle(download)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resource_check_handler(self):
        """Test resource check handler"""
        handler = ResourceCheckHandler()
        
        download = Mock()
        download.name = "test.torrent"
        download.total_size = 1024
        download.download_dir = Path(tempfile.mkdtemp())
        
        try:
            result = await handler.handle(download)
            assert result is True
        finally:
            shutil.rmtree(download.download_dir)
    
    @pytest.mark.asyncio
    async def test_handler_chain(self):
        """Test handler chain"""
        validation = ValidationHandler()
        resource = ResourceCheckHandler()
        execution = ExecutionHandler()
        
        # Build chain
        validation.set_next(resource)
        resource.set_next(execution)
        
        download = Mock()
        download.name = "test.torrent"
        download.pieces = [Mock()]
        download.total_size = 1024
        download.download_dir = Path(tempfile.mkdtemp())
        download.start_download = AsyncMock(return_value=True)
        
        try:
            result = await validation.handle(download)
            assert result is True
        finally:
            shutil.rmtree(download.download_dir)

# ============================================================================
# MEDIATOR PATTERN TESTS
# ============================================================================

class TestMediatorPattern:
    """Test Mediator Pattern implementation"""
    
    def test_mediator_registration(self):
        """Test mediator registration"""
        mediator = DownloadMediator()
        
        download = Mock()
        download.torrent_id = "test123"
        
        observer = Mock()
        handler = Mock()
        
        # Register components
        mediator.register_download(download)
        mediator.register_observer(observer)
        mediator.register_handler(handler)
        
        assert download in mediator.downloads.values()
        assert observer in mediator.observers
        assert handler in mediator.handlers
    
    @pytest.mark.asyncio
    async def test_mediator_download_start(self):
        """Test mediator download start"""
        mediator = DownloadMediator()
        
        download = Mock()
        download.torrent_id = "test123"
        download.name = "test.torrent"
        download.pieces = [Mock()]
        download.total_size = 1024
        download.download_dir = Path(tempfile.mkdtemp())
        download.start_download = AsyncMock(return_value=True)
        
        observer = Mock()
        
        mediator.register_download(download)
        mediator.register_observer(observer)
        
        try:
            result = await mediator.start_download("test123")
            assert result is True
            assert observer.update.called
        finally:
            shutil.rmtree(download.download_dir)

# ============================================================================
# MEMENTO PATTERN TESTS
# ============================================================================

class TestMementoPattern:
    """Test Memento Pattern implementation"""
    
    def test_memento_creation(self):
        """Test memento creation"""
        caretaker = DownloadCaretaker()
        
        download = Mock()
        download.torrent_id = "test123"
        download.name = "test.torrent"
        download.download_progress = 50.0
        download.downloaded_pieces = {1, 2, 3}
        download.settings = DownloadSettings()
        
        # Save state
        caretaker.save_state(download)
        
        # Verify memento was created
        memento = caretaker.get_memento("test123")
        assert memento is not None
        assert memento.torrent_id == "test123"
        assert memento.name == "test.torrent"
        assert memento.progress == 50.0
        assert memento.downloaded_pieces == {1, 2, 3}
    
    def test_memento_restoration(self):
        """Test memento restoration"""
        caretaker = DownloadCaretaker()
        
        download = Mock()
        download.torrent_id = "test123"
        download.name = "test.torrent"
        download.download_progress = 0.0
        download.downloaded_pieces = set()
        download.settings = DownloadSettings()
        
        # Save state
        caretaker.save_state(download)
        
        # Modify download
        download.download_progress = 100.0
        download.downloaded_pieces = {1, 2, 3, 4, 5}
        
        # Restore state
        result = caretaker.restore_state(download)
        assert result is True
        assert download.download_progress == 50.0
        assert download.downloaded_pieces == {1, 2, 3}

# ============================================================================
# VISITOR PATTERN TESTS
# ============================================================================

class TestVisitorPattern:
    """Test Visitor Pattern implementation"""
    
    def test_progress_visitor_single_file(self):
        """Test progress visitor for single file download"""
        visitor = ProgressVisitor()
        
        download = Mock()
        download.pieces = [Mock() for _ in range(10)]
        download.downloaded_pieces = {0, 1, 2, 3, 4}  # 5 out of 10 pieces
        download.files = []
        
        visitor.visit_single_file_download(download)
        
        assert download.download_progress == 50.0
    
    def test_progress_visitor_multi_file(self):
        """Test progress visitor for multi file download"""
        visitor = ProgressVisitor()
        
        download = Mock()
        download.files = [
            Mock(length=100, selected=True, downloaded=True),
            Mock(length=200, selected=True, downloaded=False),
            Mock(length=300, selected=False, downloaded=False)
        ]
        
        visitor.visit_multi_file_download(download)
        
        # Only selected files count, 100 downloaded out of 300 total
        assert download.download_progress == pytest.approx(33.33, rel=1e-2)
    
    def test_validation_visitor(self):
        """Test validation visitor"""
        visitor = ValidationVisitor()
        
        # Valid single file download
        download = Mock()
        download.name = "test.torrent"
        download.total_size = 1024
        download.files = []
        
        visitor.visit_single_file_download(download)  # Should not raise
        
        # Invalid single file download
        download.name = ""
        with pytest.raises(ValueError, match="Download name is required"):
            visitor.visit_single_file_download(download)

# ============================================================================
# INTERPRETER PATTERN TESTS
# ============================================================================

class TestInterpreterPattern:
    """Test Interpreter Pattern implementation"""
    
    def test_start_expression(self):
        """Test start expression"""
        expression = StartExpression()
        
        # Download is downloading and not paused
        context = {
            'download': Mock(downloading=True, paused=False)
        }
        result = expression.interpret(context)
        assert result is True
        
        # Download is paused
        context = {
            'download': Mock(downloading=True, paused=True)
        }
        result = expression.interpret(context)
        assert result is False
    
    def test_pause_expression(self):
        """Test pause expression"""
        expression = PauseExpression()
        
        # Download is downloading and paused
        context = {
            'download': Mock(downloading=True, paused=True)
        }
        result = expression.interpret(context)
        assert result is True
        
        # Download is not paused
        context = {
            'download': Mock(downloading=True, paused=False)
        }
        result = expression.interpret(context)
        assert result is False
    
    def test_complete_expression(self):
        """Test complete expression"""
        expression = CompleteExpression()
        
        # Download is completed
        context = {
            'download': Mock(completed=True)
        }
        result = expression.interpret(context)
        assert result is True
        
        # Download is not completed
        context = {
            'download': Mock(completed=False)
        }
        result = expression.interpret(context)
        assert result is False
    
    def test_and_expression(self):
        """Test AND expression"""
        left = Mock(spec=DownloadExpression)
        right = Mock(spec=DownloadExpression)
        
        expression = AndExpression(left, right)
        
        # Both true
        left.interpret.return_value = True
        right.interpret.return_value = True
        result = expression.interpret({})
        assert result is True
        
        # Left false
        left.interpret.return_value = False
        result = expression.interpret({})
        assert result is False
    
    def test_or_expression(self):
        """Test OR expression"""
        left = Mock(spec=DownloadExpression)
        right = Mock(spec=DownloadExpression)
        
        expression = OrExpression(left, right)
        
        # Both false
        left.interpret.return_value = False
        right.interpret.return_value = False
        result = expression.interpret({})
        assert result is False
        
        # Left true
        left.interpret.return_value = True
        result = expression.interpret({})
        assert result is True

# ============================================================================
# ITERATOR PATTERN TESTS
# ============================================================================

class TestIteratorPattern:
    """Test Iterator Pattern implementation"""
    
    def test_download_collection(self):
        """Test download collection"""
        collection = DownloadCollection()
        
        # Add downloads
        download1 = Mock()
        download2 = Mock()
        collection.add_download(download1)
        collection.add_download(download2)
        
        assert len(collection.downloads) == 2
    
    def test_download_iterator(self):
        """Test download iterator"""
        downloads = [Mock(), Mock(), Mock()]
        iterator = DownloadListIterator(downloads)
        
        # Test iteration
        assert iterator.has_next() is True
        assert iterator.next() == downloads[0]
        
        assert iterator.has_next() is True
        assert iterator.next() == downloads[1]
        
        assert iterator.has_next() is True
        assert iterator.next() == downloads[2]
        
        assert iterator.has_next() is False
        
        # Test StopIteration
        with pytest.raises(StopIteration):
            iterator.next()

# ============================================================================
# PROTOTYPE PATTERN TESTS
# ============================================================================

class TestPrototypePattern:
    """Test Prototype Pattern implementation"""
    
    def test_download_clone(self):
        """Test download cloning"""
        settings = DownloadSettings(speed_limit=1024)
        download = Download("test123", "test.torrent", 1024, settings)
        download.downloading = True
        download.paused = False
        download.completed = False
        download.download_progress = 50.0
        download.download_speed = 1024.0
        download.downloaded_pieces = {1, 2, 3}
        download.pieces = [Mock(), Mock()]
        download.files = [Mock(), Mock()]
        
        # Clone download
        cloned = download.clone()
        
        # Verify clone
        assert cloned.torrent_id == "test123_clone"
        assert cloned.name == "test.torrent (Clone)"
        assert cloned.total_size == 1024
        assert cloned.downloading is True
        assert cloned.paused is False
        assert cloned.completed is False
        assert cloned.download_progress == 50.0
        assert cloned.download_speed == 1024.0
        assert cloned.downloaded_pieces == {1, 2, 3}
        assert len(cloned.pieces) == 2
        assert len(cloned.files) == 2
        
        # Verify it's a different object
        assert cloned is not download

# ============================================================================
# ADAPTER PATTERN TESTS
# ============================================================================

class TestAdapterPattern:
    """Test Adapter Pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_download_adapter(self):
        """Test download adapter"""
        legacy_system = LegacyDownloadSystem()
        adapter = DownloadAdapter(legacy_system)
        
        download = Mock()
        download.torrent_id = "test123"
        download.download_dir = Path("/tmp")
        
        result = await adapter.start_download(download)
        assert result is True

# ============================================================================
# BRIDGE PATTERN TESTS
# ============================================================================

class TestBridgePattern:
    """Test Bridge Pattern implementation"""
    
    @pytest.mark.asyncio
    async def test_simulated_implementation(self):
        """Test simulated download implementation"""
        implementation = SimulatedDownloadImplementation()
        abstraction = DownloadAbstraction(implementation)
        
        result = await abstraction.download_piece(1)
        assert result is True
        
        result = await abstraction.verify_piece(1)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_real_implementation(self):
        """Test real download implementation"""
        implementation = RealDownloadImplementation()
        abstraction = DownloadAbstraction(implementation)
        
        result = await abstraction.download_piece(1)
        assert result is True
        
        result = await abstraction.verify_piece(1)
        assert result is True

# ============================================================================
# COMPOSITE PATTERN TESTS
# ============================================================================

class TestCompositePattern:
    """Test Composite Pattern implementation"""
    
    def test_download_file(self):
        """Test download file component"""
        file = DownloadFile("test.txt", 1024)
        
        assert file.get_name() == "test.txt"
        assert file.get_size() == 1024
        assert file.get_progress() == 0.0
        
        # Mark as downloaded
        file.downloaded = True
        assert file.get_progress() == 100.0
    
    def test_download_folder(self):
        """Test download folder component"""
        folder = DownloadFolder("test_folder")
        
        # Add files
        file1 = DownloadFile("file1.txt", 100)
        file2 = DownloadFile("file2.txt", 200)
        folder.add(file1)
        folder.add(file2)
        
        assert folder.get_name() == "test_folder"
        assert folder.get_size() == 300
        assert folder.get_progress() == 0.0
        
        # Mark one file as downloaded
        file1.downloaded = True
        assert folder.get_progress() == 50.0
        
        # Remove file
        folder.remove(file1)
        assert folder.get_size() == 200
        assert folder.get_progress() == 0.0

# ============================================================================
# FLYWEIGHT PATTERN TESTS
# ============================================================================

class TestFlyweightPattern:
    """Test Flyweight Pattern implementation"""
    
    def test_piece_flyweight(self):
        """Test piece flyweight"""
        flyweight = PieceFlyweight()
        
        # Get piece data
        piece1 = flyweight.get_piece_data(1)
        piece2 = flyweight.get_piece_data(2)
        piece1_again = flyweight.get_piece_data(1)
        
        assert len(piece1) == 16384
        assert len(piece2) == 16384
        assert piece1 == piece1_again  # Same piece hash returns same data
        
        # Clear cache
        flyweight.clear_cache()
        assert len(flyweight._piece_data) == 0

# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================

class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_create_download_with_patterns(self):
        """Test creating download with multiple patterns"""
        settings = DownloadSettings(speed_limit=1024)
        
        download = create_download_with_patterns(
            "test123",
            "test.torrent",
            1024,
            settings
        )
        
        assert isinstance(download, Download)
        assert download.torrent_id == "test123"
        assert download.name == "test.torrent"
        assert download.total_size == 1024
    
    def test_setup_handler_chain(self):
        """Test setting up handler chain"""
        chain = setup_handler_chain()
        
        assert isinstance(chain, ValidationHandler)
        assert chain._next_handler is not None
        assert isinstance(chain._next_handler, ResourceCheckHandler)
        assert chain._next_handler._next_handler is not None
        assert isinstance(chain._next_handler._next_handler, ExecutionHandler)
    
    def test_create_settings_builder(self):
        """Test creating settings builder"""
        builder = create_settings_builder()
        
        settings = builder.build()
        
        assert settings.speed_limit == 1024
        assert settings.upload_limit == 512
        assert settings.max_peers == 50
        assert settings.max_connections == 100
        assert settings.auto_stop is True
        assert settings.verify_pieces is True
        assert settings.pre_allocate is True

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for multiple patterns working together"""
    
    @pytest.mark.asyncio
    async def test_complete_download_workflow(self):
        """Test complete download workflow using multiple patterns"""
        # Create download using factory
        settings = DownloadSettings(speed_limit=1024)
        download = DownloadFactory.create_download(
            DownloadType.SINGLE_FILE,
            torrent_id="test123",
            name="test.torrent",
            total_size=1024,
            settings=settings
        )
        
        # Setup observer
        subject = DownloadSubject()
        observer = Mock(spec=DownloadObserver)
        subject.attach(observer)
        
        # Setup mediator
        mediator = DownloadMediator()
        mediator.register_download(download)
        mediator.register_observer(observer)
        
        # Setup handler chain
        chain = setup_handler_chain()
        mediator.register_handler(chain)
        
        # Setup caretaker for state management
        caretaker = DownloadCaretaker()
        caretaker.save_state(download)
        
        # Start download through mediator
        result = await mediator.start_download("test123")
        
        assert result is True
        assert observer.update.called
        
        # Verify state was saved
        memento = caretaker.get_memento("test123")
        assert memento is not None
        assert memento.torrent_id == "test123"
    
    def test_pattern_combinations(self):
        """Test various pattern combinations"""
        # Builder + Factory
        settings = (DownloadSettingsBuilder()
                   .with_speed_limit(1024)
                   .with_auto_stop(True)
                   .build())
        
        download = DownloadFactory.create_download(
            DownloadType.SINGLE_FILE,
            torrent_id="test123",
            name="test.torrent",
            total_size=1024,
            settings=settings
        )
        
        assert download.settings.speed_limit == 1024
        assert download.settings.auto_stop is True
        
        # Prototype + Memento
        cloned = download.clone()
        caretaker = DownloadCaretaker()
        caretaker.save_state(cloned)
        
        memento = caretaker.get_memento("test123_clone")
        assert memento is not None
        assert memento.name == "test.torrent (Clone)"

# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance tests for design patterns"""
    
    def test_flyweight_memory_efficiency(self):
        """Test flyweight pattern memory efficiency"""
        import sys
        
        flyweight = PieceFlyweight()
        
        # Get initial memory usage
        initial_memory = sys.getsizeof(flyweight._piece_data)
        
        # Create many pieces
        for i in range(1000):
            flyweight.get_piece_data(i)
        
        # Memory should not grow linearly
        final_memory = sys.getsizeof(flyweight._piece_data)
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 1000000  # Less than 1MB
    
    @pytest.mark.asyncio
    async def test_observer_performance(self):
        """Test observer pattern performance"""
        import time
        
        subject = DownloadSubject()
        
        # Create many observers
        observers = [Mock(spec=DownloadObserver) for _ in range(100)]
        for observer in observers:
            subject.attach(observer)
        
        # Measure notification time
        start_time = time.time()
        
        for _ in range(1000):
            subject.notify("test123", 50.0, 1024.0)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete within reasonable time
        assert total_time < 1.0  # Less than 1 second
        
        # All observers should be notified
        for observer in observers:
            assert observer.update.call_count == 1000

# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling in design patterns"""
    
    def test_factory_error_handling(self):
        """Test factory error handling"""
        # Clear registrations
        DownloadFactory._download_types.clear()
        
        with pytest.raises(ValueError, match="Unknown download type"):
            DownloadFactory.create_download(DownloadType.SINGLE_FILE)
    
    def test_observer_error_handling(self):
        """Test observer error handling"""
        subject = DownloadSubject()
        
        # Create observer that raises exception
        observer = Mock(spec=DownloadObserver)
        observer.update.side_effect = Exception("Observer error")
        subject.attach(observer)
        
        # Should not raise exception
        subject.notify("test123", 50.0, 1024.0)
        
        # Observer should still be called
        assert observer.update.called
    
    @pytest.mark.asyncio
    async def test_template_error_handling(self):
        """Test template method error handling"""
        download = Mock()
        download.name = "test.torrent"
        download.downloading = True
        download.pieces = [Mock()]
        download.downloaded_pieces = set()
        
        template = SimulatedDownloadTemplate(download)
        
        # Mock error in download_pieces
        with patch.object(template, 'download_pieces', side_effect=Exception("Test error")):
            result = await template.execute_download()
            assert result is False

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "--tb=short"]) 