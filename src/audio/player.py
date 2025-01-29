from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from utils.constants import UPDATE_INTERVAL, DEFAULT_VOLUME

class AudioPlayer(QObject):
    position_changed = pyqtSignal(float)  # Current position in seconds
    playback_state_changed = pyqtSignal(bool)  # True if playing
    
    def __init__(self):
        super().__init__()
        self._setup_player()
        self._setup_timer()
        self.duration = 0
        
    def _setup_player(self):
        """Initialize QMediaPlayer and audio output"""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(DEFAULT_VOLUME)
        
        # Connect signals
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        
    def _setup_timer(self):
        """Setup update timer for position tracking"""
        self.update_timer = QTimer()
        self.update_timer.setInterval(UPDATE_INTERVAL)
        self.update_timer.timeout.connect(self._update_position)
        
    def _on_duration_changed(self, duration):
        """Handle duration changes in milliseconds"""
        self.duration = duration / 1000  # Convert to seconds
        
    def _on_position_changed(self, position):
        """Handle position changes in milliseconds"""
        self.position_changed.emit(position / 1000)  # Convert to seconds
        
    def _update_position(self):
        """Update current position during playback"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            position = self.player.position() / 1000  # Convert to seconds
            self.position_changed.emit(position)
            
            # Check if we've reached the end
            if position >= self.duration:
                self.stop()
                
    def set_source(self, file_path):
        """Set the audio source file"""
        from PyQt6.QtCore import QUrl
        self.player.setSource(QUrl.fromLocalFile(file_path))
        
    def play(self):
        """Start or resume playback"""
        self.player.play()
        self.update_timer.start()
        self.playback_state_changed.emit(True)
        
    def pause(self):
        """Pause playback"""
        self.player.pause()
        self.update_timer.stop()
        self.playback_state_changed.emit(False)
        
    def stop(self):
        """Stop playback and reset position"""
        self.player.stop()
        self.update_timer.stop()
        self.playback_state_changed.emit(False)
        self.position_changed.emit(0)
        
    def set_position(self, seconds):
        """Set playback position in seconds"""
        self.player.setPosition(int(seconds * 1000))
        
    def set_volume(self, volume):
        """Set volume level (0.0 to 1.0)"""
        self.audio_output.setVolume(volume)
        
    def cleanup(self):
        """Clean up resources"""
        self.stop()
        self.update_timer.stop() 