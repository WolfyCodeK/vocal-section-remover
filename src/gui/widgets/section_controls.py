from PyQt6.QtWidgets import (
    QWidget,
    QPushButton, 
    QLabel, 
    QVBoxLayout, 
    QHBoxLayout, 
    QListWidget, 
)
from PyQt6.QtCore import pyqtSignal
from utils.time_format import format_time_precise
from utils.constants import COLORS

class SectionControls(QWidget):
    section_added = pyqtSignal(tuple)  # (start_time, end_time)
    section_deleted = pyqtSignal(int)  # section index
    process_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_start = None
        self.current_end = None
        self.sections = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Selection controls
        selection_layout = QHBoxLayout()
        self.mark_start_button = QPushButton("Mark Start")
        self.mark_end_button = QPushButton("Mark End")
        selection_layout.addWidget(self.mark_start_button)
        selection_layout.addWidget(self.mark_end_button)
        layout.addLayout(selection_layout)
        
        # Selection display
        self.selection_label = QLabel("No section selected")
        self.selection_label.setStyleSheet(f"color: {COLORS['INFO']};")
        layout.addWidget(self.selection_label)
        
        # Add/Cancel buttons
        buttons_layout = QHBoxLayout()
        self.add_section_button = QPushButton("Add Section")
        self.cancel_button = QPushButton("Cancel")
        buttons_layout.addWidget(self.add_section_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        
        # Sections list
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # Process controls
        bottom_layout = QHBoxLayout()
        self.delete_button = QPushButton("Delete Section")
        self.process_button = QPushButton("Process Sections")
        self.process_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['SUCCESS']};
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #45a049;
            }}
        """)
        bottom_layout.addWidget(self.delete_button)
        bottom_layout.addWidget(self.process_button)
        layout.addLayout(bottom_layout)
        
        # Connect signals
        self.mark_start_button.clicked.connect(self.mark_start)
        self.mark_end_button.clicked.connect(self.mark_end)
        self.add_section_button.clicked.connect(self.add_section)
        self.cancel_button.clicked.connect(self.cancel_selection)
        self.delete_button.clicked.connect(self.delete_section)
        self.process_button.clicked.connect(self.process_requested.emit)
        
        # Initial button states
        self.add_section_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self.set_button_highlight(self.mark_start_button, True) 

    def set_button_highlight(self, button, highlighted=True):
        """Set highlight state for a button"""
        if highlighted:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['HIGHLIGHT']};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['HIGHLIGHT_HOVER']};
                }}
            """)
        else:
            button.setStyleSheet("")

    def mark_start(self, position=None):
        """Mark the start of a section"""
        if position is not None:
            self.current_start = position
            self.set_button_highlight(self.mark_start_button, False)
            self.set_button_highlight(self.mark_end_button, True)
            self.cancel_button.setEnabled(True)
            self.update_selection_label()

    def mark_end(self, position=None):
        """Mark the end of a section"""
        if position is not None and self.current_start is not None:
            if position > self.current_start:
                self.current_end = position
                self.set_button_highlight(self.mark_end_button, False)
                self.set_button_highlight(self.add_section_button, True)
                self.add_section_button.setEnabled(True)
                self.update_selection_label()

    def add_section(self):
        """Add the current section"""
        if self.current_start is not None and self.current_end is not None:
            section = (self.current_start, self.current_end)
            self.sections.append(section)
            self.section_added.emit(section)
            
            # Update list widget
            start_str = format_time_precise(self.current_start)
            end_str = format_time_precise(self.current_end)
            self.list_widget.addItem(f"Section {len(self.sections)}: {start_str} to {end_str}")
            
            # Reset selection
            self.cancel_selection()
            self.process_button.setEnabled(True)

    def cancel_selection(self):
        """Cancel current section selection"""
        self.current_start = None
        self.current_end = None
        self.add_section_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.set_button_highlight(self.mark_start_button, True)
        self.set_button_highlight(self.mark_end_button, False)
        self.set_button_highlight(self.add_section_button, False)
        self.update_selection_label()

    def delete_section(self):
        """Delete selected section"""
        current_row = self.list_widget.currentRow()
        if current_row >= 0:
            self.list_widget.takeItem(current_row)
            self.sections.pop(current_row)
            self.section_deleted.emit(current_row)
            
            # Update remaining section numbers
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                start_str = format_time_precise(self.sections[i][0])
                end_str = format_time_precise(self.sections[i][1])
                item.setText(f"Section {i + 1}: {start_str} to {end_str}")
            
            # Disable process button if no sections remain
            if not self.sections:
                self.process_button.setEnabled(False)

    def update_selection_label(self):
        """Update the selection display label"""
        if self.current_start is not None:
            start_str = format_time_precise(self.current_start)
            if self.current_end is not None:
                end_str = format_time_precise(self.current_end)
                self.selection_label.setText(f"Selected: {start_str} to {end_str}")
            else:
                self.selection_label.setText(f"Start: {start_str} - Click 'Mark End' to set end point")
        else:
            self.selection_label.setText("No section selected") 