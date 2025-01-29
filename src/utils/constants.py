from PyQt6.QtCore import Qt

# Window dimensions
MIN_WINDOW_WIDTH = 500
MIN_WINDOW_HEIGHT = 550

# Layout constants
MIN_TOP_ROW_HEIGHT = 100
MIN_TIMELINE_HEIGHT = 180
MIN_SECTION_HEIGHT = 250
MIN_STATUS_HEIGHT = 20
LAYOUT_SPACING = 10
LAYOUT_MARGINS = 20

# Audio constants
SEEK_COOLDOWN = 50  # milliseconds
UPDATE_INTERVAL = 100  # milliseconds
DEFAULT_VOLUME = 0.5

# Keyboard shortcuts
SHORTCUTS = {
    'PLAY_PAUSE': Qt.Key.Key_Space,
    'SEEK_BACK': Qt.Key.Key_Left,
    'SEEK_FORWARD': Qt.Key.Key_Right,
    'VOLUME_UP': Qt.Key.Key_Up,
    'VOLUME_DOWN': Qt.Key.Key_Down,
    'MARK_SECTION': Qt.Key.Key_Return,
}

# Colors
COLORS = {
    'HIGHLIGHT': '#FF4444',
    'HIGHLIGHT_HOVER': '#FF6666',
    'ERROR': '#ff4444',
    'INFO': '#3498db',
    'SUCCESS': '#4CAF50',
} 