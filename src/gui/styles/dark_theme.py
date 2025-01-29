def apply_dark_theme(app):
    """Apply dark theme to the application"""
    dark_stylesheet = """
    QMainWindow, QWidget {
        background-color: #2E2E2E;
        color: #FFFFFF;
    }
    QLabel {
        color: #FFFFFF;
    }
    QPushButton {
        background-color: #444444;
        color: #FFFFFF;
        border: 1px solid #555555;
        border-radius: 5px;
        padding: 5px;
    }
    QPushButton:hover {
        background-color: #555555;
    }
    /* ... rest of the dark theme styles ... */
    """
    app.setStyleSheet(dark_stylesheet) 