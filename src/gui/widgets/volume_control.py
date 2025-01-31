from PyQt6.QtWidgets import (
    QWidget, 
    QSlider, 
    QLabel, 
    QHBoxLayout, 
    QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from utils.constants import DEFAULT_VOLUME

class VolumeControl(QWidget):
    volume_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        group = QGroupBox("Volume")
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(25, 0, -5, 5)
        
        # Volume icon
        volume_label = QLabel("🔊")
        layout.addWidget(volume_label)
        
        # Volume slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(DEFAULT_VOLUME * 100))
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(25)
        self.slider.valueChanged.connect(self._on_value_changed)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.slider, stretch=1)
        
        # Percentage label
        self.percentage = QLabel(f"{int(DEFAULT_VOLUME * 100)}%")
        self.percentage.setFixedWidth(40)
        layout.addWidget(self.percentage)
        
        group.setLayout(layout)
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(group)
        
    def _on_value_changed(self):
        value = self.slider.value() / 100
        self.percentage.setText(f"{int(value * 100)}%")
        self.volume_changed.emit(value) 