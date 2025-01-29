from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from utils.constants import COLORS

class StatusBar(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.set_status("Ready")
        
    def set_status(self, message, is_error=False):
        """Update status message with appropriate styling"""
        color = COLORS['ERROR'] if is_error else COLORS['INFO']
        self.setStyleSheet(f"""
            color: {color};
            font-size: 13px;
            font-weight: bold;
            padding: 0px;
            margin: 0px;
        """)
        self.setText(message) 