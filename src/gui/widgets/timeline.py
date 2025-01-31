from PyQt6.QtWidgets import (
    QWidget, 
    QSlider, 
    QLabel, 
    QVBoxLayout, 
    QHBoxLayout, 
    QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from utils.time_format import format_time_precise

class Timeline(QWidget):
    position_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.was_playing = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Time display
        self.time_display = QLabel("00:00.00 / 00:00.00")
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_display)
        
        # Timeline slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.sliderPressed.connect(self._on_press)
        self.slider.sliderReleased.connect(self._on_release)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)
        
        # Playback controls
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        self.back_button = QPushButton()
        self.play_button = QPushButton()
        self.forward_button = QPushButton()
        
        for button in [self.back_button, self.play_button, self.forward_button]:
            button.setFixedSize(24, 24)
            button.setStyleSheet("""
                QPushButton {
                    padding: 0px;
                    background-color: #3E3E3E;
                }
                QPushButton:hover {
                    background-color: #4E4E4E;
                }
            """)
            controls_layout.addWidget(button)
            
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
    def _on_press(self):
        self.slider.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.position_changed.emit(self.slider.value() / 100)
        
    def _on_release(self):
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def _on_value_changed(self):
        self.position_changed.emit(self.slider.value() / 100)
        
    def set_duration(self, duration):
        """Set timeline duration in seconds"""
        self.slider.setMaximum(int(duration * 100))
        
    def update_position(self, position, duration):
        """Update current position and time display"""
        self.slider.blockSignals(True)
        self.slider.setValue(int(position * 100))
        self.slider.blockSignals(False)
        
        position_str = format_time_precise(position)
        duration_str = format_time_precise(duration)
        self.time_display.setText(f"{position_str} / {duration_str}") 