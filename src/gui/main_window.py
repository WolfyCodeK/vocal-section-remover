from PyQt6.QtWidgets import (
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton, 
    QFileDialog, 
    QGroupBox, 
    QLabel, 
    QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
import os

from .widgets.timeline import Timeline
from .widgets.volume_control import VolumeControl
from .widgets.section_controls import SectionControls
from .widgets.status_bar import StatusBar
from audio.player import AudioPlayer
from audio.file_loader import FileLoader
from audio.processor import AudioProcessor
from utils.constants import (
    MIN_WINDOW_WIDTH, 
    MIN_WINDOW_HEIGHT, 
    SHORTCUTS
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.song = None
        self.song_path = None
        self.audio_processor = None
        
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_audio_player()
        
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Voice Section Remover")
        self.setMinimumWidth(MIN_WINDOW_WIDTH)
        self.setMinimumHeight(MIN_WINDOW_HEIGHT)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add components
        self._setup_top_row(main_layout)
        self._setup_timeline(main_layout)
        self._setup_section_controls(main_layout)
        self._setup_status_bar(main_layout)
        
    def _setup_top_row(self, main_layout):
        """Setup load button and volume controls"""
        top_row = QHBoxLayout()
        
        # Load button group
        load_group = QGroupBox("Load Song")
        load_layout = QVBoxLayout()
        self.load_button = QPushButton(" Import File")
        self.load_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.load_button.clicked.connect(self.load_file)
        self.load_button.setMinimumWidth(200)
        self.load_button.setFixedHeight(35)
        load_layout.addWidget(self.load_button, alignment=Qt.AlignmentFlag.AlignCenter)
        load_group.setLayout(load_layout)
        
        # Volume control
        self.volume_control = VolumeControl()
        
        top_row.addWidget(load_group)
        top_row.addWidget(self.volume_control, stretch=1)
        main_layout.addLayout(top_row) 

    def _setup_timeline(self, main_layout):
        """Setup timeline and playback controls"""
        timeline_group = QGroupBox("Timeline")
        timeline_layout = QVBoxLayout()
        
        # Song name label
        self.song_label = QLabel("No song loaded")
        self.song_label.setStyleSheet("color: gray; font-style: italic; padding: 2px;")
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timeline_layout.addWidget(self.song_label)
        
        # Timeline widget
        self.timeline = Timeline()
        timeline_layout.addWidget(self.timeline)
        
        timeline_group.setLayout(timeline_layout)
        main_layout.addWidget(timeline_group)
        
    def _setup_section_controls(self, main_layout):
        """Setup section marking and processing controls"""
        self.section_controls = SectionControls()
        main_layout.addWidget(self.section_controls)
        
        # Connect section control signals
        self.section_controls.section_added.connect(self._on_section_added)
        self.section_controls.section_deleted.connect(self._on_section_deleted)
        self.section_controls.process_requested.connect(self.process_sections)
        
    def _setup_status_bar(self, main_layout):
        """Setup status bar"""
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)
        
    def setup_audio_player(self):
        """Initialize audio player and connect signals"""
        self.player = AudioPlayer()
        
        # Connect player signals
        self.player.position_changed.connect(self._on_position_changed)
        self.player.playback_state_changed.connect(self._on_playback_state_changed)
        
        # Connect volume control
        self.volume_control.volume_changed.connect(self.player.set_volume)
        
        # Connect timeline controls
        self.timeline.position_changed.connect(self.player.set_position)
        
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        shortcuts = {
            SHORTCUTS['PLAY_PAUSE']: self.toggle_play,
            SHORTCUTS['SEEK_BACK']: lambda: self.adjust_time(-1.0),
            SHORTCUTS['SEEK_FORWARD']: lambda: self.adjust_time(1.0),
            SHORTCUTS['VOLUME_UP']: lambda: self.adjust_volume(5),
            SHORTCUTS['VOLUME_DOWN']: lambda: self.adjust_volume(-5),
            SHORTCUTS['MARK_SECTION']: self.handle_mark_shortcut
        }
        
        for key, slot in shortcuts.items():
            QShortcut(QKeySequence(key), self).activated.connect(slot)
            
    def load_file(self):
        """Open file dialog and load audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.mp3 *.wav);;All Files (*.*)"
        )
        
        if file_path:
            # Clean up previous file
            if self.song:
                self.cleanup_current_file()
            
            # Disable UI during loading
            self.setEnabled(False)
            self.status_bar.set_status("Loading file...")
            
            # Start file loader
            self.file_loader = FileLoader(file_path)
            self.file_loader.finished.connect(self._on_file_loaded)
            self.file_loader.status_update.connect(self.status_bar.set_status)
            self.file_loader.start()
            
    def cleanup_current_file(self):
        """Clean up resources from current file"""
        if hasattr(self, 'player'):
            self.player.stop()
        
        self.song = None
        self.song_path = None
        self.section_controls.sections.clear()
        self.section_controls.list_widget.clear()
        self.section_controls.cancel_selection()
        self.timeline.update_position(0, 0)
        self.song_label.setText("No song loaded")
        self.song_label.setStyleSheet("color: gray; font-style: italic;")
        
    def _on_file_loaded(self, result):
        """Handle loaded audio file"""
        song, file_path = result
        
        if song is None:
            self.setEnabled(True)
            return
            
        # Update state
        self.song = song
        self.song_path = file_path
        self.player.set_source(file_path)
        
        # Update UI
        filename = os.path.basename(file_path)
        self.setWindowTitle(f"Voice Section Remover - {filename}")
        self.song_label.setText(filename)
        self.song_label.setStyleSheet("color: white; font-style: normal;")
        self.status_bar.set_status("File loaded successfully")
        
        # Re-enable UI
        self.setEnabled(True)
        
    def toggle_play(self):
        """Toggle play/pause"""
        if not self.song:
            self.status_bar.set_status("No song loaded!", is_error=True)
            return
            
        if self.player.is_playing:
            self.player.pause()
        else:
            self.player.play()
            
    def adjust_time(self, delta):
        """Adjust playback position"""
        if not self.song:
            return
            
        current_pos = self.player.position / 1000  # Convert to seconds
        new_pos = max(0, min(current_pos + delta, self.song.duration_seconds))
        self.player.set_position(new_pos)
        
    def adjust_volume(self, delta):
        """Adjust volume level"""
        current_volume = self.volume_control.slider.value()
        new_volume = max(0, min(100, current_volume + delta))
        self.volume_control.slider.setValue(new_volume)
        
    def handle_mark_shortcut(self):
        """Handle Enter key for section marking"""
        if not self.song:
            self.status_bar.set_status("No song loaded!", is_error=True)
            return
            
        current_pos = self.player.position / 1000
        
        if self.section_controls.current_start is None:
            self.section_controls.mark_start(current_pos)
        elif self.section_controls.current_end is None:
            self.section_controls.mark_end(current_pos)
        elif self.section_controls.add_section_button.isEnabled():
            self.section_controls.add_section()
            
    def process_sections(self):
        """Start processing sections"""
        if not self.song or not self.section_controls.sections:
            self.status_bar.set_status("No sections to process!", is_error=True)
            return
            
        self.audio_processor = AudioProcessor(
            self.song,
            self.section_controls.sections,
            self.song_path
        )
        self.audio_processor.status_update.connect(self.status_bar.set_status)
        self.audio_processor.start()
        
    def closeEvent(self, event):
        """Handle application closure"""
        # Stop playback and cleanup
        if hasattr(self, 'player'):
            self.player.cleanup()
            
        # Stop processor if running
        if self.audio_processor and self.audio_processor.isRunning():
            self.audio_processor.terminate()
            
        event.accept()

    def _on_section_added(self, section):
        """Handle when a new section is added"""
        # Currently just used for signal connection, could add additional handling if needed
        pass

    def _on_section_deleted(self, index):
        """Handle when a section is deleted"""
        # Currently just used for signal connection, could add additional handling if needed
        pass

    def _on_position_changed(self, position):
        """Handle audio position changes"""
        if self.song:
            self.timeline.update_position(position, self.song.duration_seconds)

    def _on_playback_state_changed(self, is_playing):
        """Handle playback state changes"""
        if is_playing:
            self.timeline.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.timeline.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)) 