import os
import pygame
import sys
from pydub import AudioSegment
import subprocess
import shutil
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QListWidget,
    QLineEdit,
    QWidget,
    QGroupBox,
    QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon
import resources

# Initialize Pygame mixer
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
pygame.mixer.music.set_volume(1.0)  # Set initial volume to maximum

# Ensure the output directory exists
os.makedirs('output/temp_section', exist_ok=True)

def apply_dark_mode(app):
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
    QLineEdit {
        background-color: #3E3E3E;
        color: #FFFFFF;
        border: 1px solid #555555;
        border-radius: 5px;
        padding: 5px;
    }
    QListWidget {
        background-color: #3E3E3E;
        color: #FFFFFF;
        border: 1px solid #555555;
        border-radius: 5px;
    }
    QSlider::groove:horizontal {
        background: #3E3E3E;
        height: 5px;
    }
    QSlider::handle:horizontal {
        background: #FFFFFF;
        border: 1px solid #555555;
        width: 10px;
        margin: -5px 0;
        border-radius: 5px;
    }
    QSlider::groove:vertical {
        background: #3E3E3E;
        width: 5px;
    }
    QSlider::handle:vertical {
        background: #FFFFFF;
        border: 1px solid #555555;
        height: 10px;
        margin: 0 -5px;
        border-radius: 5px;
    }
    QGroupBox {
        border: 1px solid #555555;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 5px;
        color: #FFFFFF;
        background-color: #2E2E2E;
    }
    QLabel[volume="true"] {
        font-size: 14px;
        min-width: 40px;
        padding: 2px;
    }
    QSlider::handle:vertical {
        background: #FFFFFF;
        border: 1px solid #555555;
        height: 10px;
        margin: 0 -4px;
        border-radius: 5px;
    }
    QSlider::groove:vertical {
        background: #3E3E3E;
        width: 3px;
    }
    """
    app.setStyleSheet(dark_stylesheet)

class AudioProcessor(QThread):
    status_update = pyqtSignal(str)

    def __init__(self, song, sections):
        super().__init__()
        self.song = song
        self.sections = sections

    def run(self):
        # Sort sections by start time to ensure they are processed in order
        self.sections.sort(key=lambda x: x[0])

        combined = AudioSegment.empty()  # Start with an empty audio segment
        last_end_time = 0  # Keep track of the last section's end time

        for idx, (start_time, end_time) in enumerate(self.sections, start=1):
            self.status_update.emit(f"Section {idx} processing from {start_time}s to {end_time}s...")
            # Slice the song to the selected section
            section = self.song[start_time * 1000:end_time * 1000]  # times in milliseconds
            section.export("temp_section.wav", format="wav")  # Export as WAV for better separation

            self.status_update.emit(f"Running Demucs for section {idx}...")
            # Run Demucs with completely hidden console
            startupinfo = None
            if os.name == 'nt':  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW | subprocess.CREATE_NO_WINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            # Create a complete subprocess configuration
            subprocess.run(
                ["demucs", "-n", "htdemucs", "--two-stems=vocals", "temp_section.wav"],
                startupinfo=startupinfo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                shell=False
            )

            self.status_update.emit(f"Loading instrumental version for section {idx}...")
            # Ensure the directory exists and the file is created
            instrumental_path = os.path.join('separated', 'htdemucs', 'temp_section', 'no_vocals.wav')
            if not os.path.exists(instrumental_path):
                self.status_update.emit(f"Error: Instrumental file not found for section {idx}")
                return

            # Load instrumental version (no_vocals.wav contains the instrumental track)
            instrumental = AudioSegment.from_file(instrumental_path)

            self.status_update.emit(f"Adding song parts for section {idx}...")
            # Add the part before the section if necessary
            if start_time > last_end_time:
                part_before_section = self.song[last_end_time * 1000:start_time * 1000]
                combined += part_before_section

            # Add the section with vocals (original section)
            section_with_vocals = section
            combined += section_with_vocals

            # Add the section without vocals (instrumental version)
            section_without_vocals = instrumental
            combined += section_without_vocals

            last_end_time = end_time  # Update the last end time to the current section's end time

        # Add the remaining part of the song after the last section
        if last_end_time < len(self.song) / 1000:  # Ensure there's more of the song after the last section
            remaining_part = self.song[last_end_time * 1000:]
            combined += remaining_part

        self.status_update.emit("Exporting final result...")
        # Export the final combined result
        combined.export("output_with_vocals_removed.mp3", format="mp3")

        self.status_update.emit("Cleaning up temporary files...")
        # Clean up temporary files
        os.remove("temp_section.wav")
        shutil.rmtree("separated", ignore_errors=True)
        self.status_update.emit("Processing complete! Saved as output_with_vocals_removed.mp3")

class AudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window icon
        icon_path = resources.get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        # Initialize pygame mixer with better audio quality
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.music.set_volume(1.0)  # Set initial volume to maximum
        
        self.initUI()
        self.song = None
        self.song_path = None
        self.sections = []
        self.is_playing = False
        self.current_time = 0
        self.song_length = 0
        self.audio_processor = None
        self.selecting_start = False
        self.selecting_end = False
        self.current_section_start = None
        self.current_section_end = None

    def initUI(self):
        self.setWindowTitle("Audio Section Editor")
        self.setGeometry(300, 300, 500, 600)

        # Main layout
        main_layout = QVBoxLayout()

        # Song loading section
        song_group = QGroupBox("Load Song")
        song_layout = QVBoxLayout()
        self.load_button = QPushButton("Load Song")
        self.load_button.setIcon(self.style().standardIcon(QPushButton().style().SP_DirOpenIcon))
        self.load_button.clicked.connect(self.load_song)
        self.song_label = QLabel("No song loaded")
        self.song_label.setStyleSheet("color: gray; font-style: italic;")
        song_layout.addWidget(self.load_button)
        song_layout.addWidget(self.song_label)
        song_group.setLayout(song_layout)
        main_layout.addWidget(song_group)

        # Playback controls
        playback_group = QGroupBox("Playback Controls")
        playback_layout = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.setIcon(self.style().standardIcon(QPushButton().style().SP_MediaPlay))
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setIcon(self.style().standardIcon(QPushButton().style().SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_audio)
        playback_layout.addWidget(self.play_button)
        playback_layout.addWidget(self.stop_button)
        playback_group.setLayout(playback_layout)
        main_layout.addWidget(playback_group)

        # Timeline and volume layout
        timeline_volume_row = QHBoxLayout()
        
        # Timeline group
        timeline_group = QGroupBox("Timeline")
        timeline_layout = QVBoxLayout()
        
        # Add time display label
        self.time_display = QLabel("00:00 / 00:00")
        timeline_layout.addWidget(self.time_display)
        
        # Timeline slider
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setRange(0, 100)
        self.timeline_slider.valueChanged.connect(self.on_slider_change)
        timeline_layout.addWidget(self.timeline_slider)
        
        timeline_group.setLayout(timeline_layout)
        timeline_volume_row.addWidget(timeline_group)
        
        # Volume group
        volume_group = QGroupBox("Volume")
        volume_group.setFixedWidth(80)  # Make it narrow
        volume_layout = QVBoxLayout()
        volume_layout.setSpacing(2)  # Reduce spacing between elements
        
        # Volume icon/label
        volume_label = QLabel("🔊")  # Unicode speaker icon
        volume_label.setAlignment(Qt.AlignCenter)
        volume_layout.addWidget(volume_label)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Vertical)
        self.volume_slider.setFixedHeight(80)  # Make it shorter
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)  # Set initial value to maximum
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_slider.setTickPosition(QSlider.TicksBothSides)
        self.volume_slider.setTickInterval(25)
        volume_layout.addWidget(self.volume_slider, alignment=Qt.AlignCenter)
        
        # Volume percentage
        self.volume_percentage = QLabel("100%")
        self.volume_percentage.setAlignment(Qt.AlignCenter)
        volume_layout.addWidget(self.volume_percentage)
        
        volume_group.setLayout(volume_layout)
        timeline_volume_row.addWidget(volume_group)
        
        main_layout.addLayout(timeline_volume_row)

        # Section controls
        section_group = QGroupBox("Sections")  
        section_layout = QVBoxLayout()
        
        # Timeline selection buttons
        selection_buttons_layout = QHBoxLayout()
        self.mark_start_button = QPushButton("Mark Start")
        self.mark_start_button.clicked.connect(self.start_selection)
        self.mark_end_button = QPushButton("Mark End")
        self.mark_end_button.clicked.connect(self.end_selection)
        selection_buttons_layout.addWidget(self.mark_start_button)
        selection_buttons_layout.addWidget(self.mark_end_button)
        section_layout.addLayout(selection_buttons_layout)
        
        # Current selection display
        self.selection_label = QLabel("No section selected")
        self.selection_label.setStyleSheet("color: #00B4FF;")
        section_layout.addWidget(self.selection_label)
        
        # Add section button
        self.add_section_button = QPushButton("Add Section")
        self.add_section_button.clicked.connect(self.add_section)
        self.add_section_button.setEnabled(False)  # Disabled until a valid selection is made
        section_layout.addWidget(self.add_section_button)
        
        # Section list
        self.section_list_widget = QListWidget()
        section_layout.addWidget(self.section_list_widget)
        
        # Delete section button
        self.delete_section_button = QPushButton("Delete Selected Section")
        self.delete_section_button.clicked.connect(self.delete_section)
        section_layout.addWidget(self.delete_section_button)
        
        section_group.setLayout(section_layout)
        main_layout.addWidget(section_group)

        # Process button
        self.process_button = QPushButton("Process Sections")
        self.process_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.process_button.clicked.connect(self.process_sections)
        main_layout.addWidget(self.process_button)

        # Status label
        self.status_label = QLabel("Status: Waiting for song...")
        self.status_label.setStyleSheet("""
            color: #00B4FF;  /* Bright blue color */
            font-size: 14px;
            font-weight: bold;
            padding: 5px;
            background-color: #363636;  /* Slightly lighter than background for contrast */
            border-radius: 4px;
        """)
        main_layout.addWidget(self.status_label)

        # Apply main layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Apply stylesheet for modern look
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F7F7F7;
            }
            QPushButton {
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
                outline: none;  /* Remove outline */
            }
            QPushButton:focus {
                outline: none;  /* Remove focus outline */
                border: 1px solid #555555;  /* Keep consistent border */
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 6px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #D0D0D0;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
            QLabel {
                font-size: 12px;
            }
            QSlider {
                height: 20px;
            }
        """)
        
    def load_song(self):
        file, _ = QFileDialog.getOpenFileName(self, "Load Song", "", "Audio Files (*.mp3 *.wav)")
        if file:
            self.song_path = file
            self.song = AudioSegment.from_file(file)
            self.song_label.setText(f"Loaded: {os.path.basename(self.song_path)}")
            self.status_label.setText("Song loaded successfully!")

            # Calculate the song length using AudioSegment
            self.song_length = len(self.song) / 1000  # Convert milliseconds to seconds
            self.timeline_slider.setRange(0, int(self.song_length))
            self.current_time = 0

            # Load the audio file using pygame
            pygame.mixer.music.load(file)

    def toggle_play(self):
        if self.song is None:
            self.status_label.setText("Error: No song loaded!")
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.play_button.setText("Play")
        else:
            if self.current_time == 0:
                pygame.mixer.music.play()  # Start from beginning
            else:
                pygame.mixer.music.play(start=self.current_time)
            self.play_button.setText("Pause")
            self.update_time()  # Start updating the time display
        self.is_playing = not self.is_playing

    def stop_audio(self):
        pygame.mixer.music.stop()
        self.play_button.setText("Play")
        self.is_playing = False
        self.current_time = 0
        self.timeline_slider.setValue(0)

    def update_time(self):
        if self.is_playing:
            # Get the current time of the song (in seconds)
            pos = pygame.mixer.music.get_pos()
            if pos == -1:  # Music has stopped
                self.stop_audio()
                return
                
            self.current_time = pos / 1000.0
            self.timeline_slider.setValue(int(self.current_time))
            
            # Update the time display
            minutes, seconds = divmod(int(self.current_time), 60)
            total_minutes, total_seconds = divmod(int(self.song_length), 60)
            self.time_display.setText(f"{minutes:02}:{seconds:02} / {total_minutes:02}:{total_seconds:02}")
            
            # Continue updating the time every 100ms
            QTimer.singleShot(100, self.update_time)

    def on_slider_change(self):
        if not self.song:  # Check if song is loaded
            return
            
        # Update the current time when the slider is moved
        self.current_time = self.timeline_slider.value()
        
        if self.is_playing:
            pygame.mixer.music.play(start=self.current_time)

        # Update the time display
        minutes, seconds = divmod(int(self.current_time), 60)
        total_minutes, total_seconds = divmod(int(self.song_length), 60)
        self.time_display.setText(f"{minutes:02}:{seconds:02} / {total_minutes:02}:{total_seconds:02}")

    def set_volume(self):
        volume = self.volume_slider.value() / 100.0  # Convert to a float between 0 and 1
        pygame.mixer.music.set_volume(volume)
        self.volume_percentage.setText(f"{int(volume * 100)}%")

    def start_selection(self):
        if not self.song:
            self.status_label.setText("Error: No song loaded!")
            return
        
        # Use current timeline position immediately
        self.current_section_start = self.current_time
        self.mark_start_button.setStyleSheet("background-color: #FF4444;")
        self.mark_end_button.setStyleSheet("")
        self.update_selection_label()
        self.status_label.setText("Start point marked. Click 'Mark End' to set end point")
        
    def end_selection(self):
        if not self.song:
            self.status_label.setText("Error: No song loaded!")
            return
        
        if self.current_section_start is None:
            self.status_label.setText("Error: Set start point first!")
            return
        
        # Use current timeline position immediately
        if self.current_time > self.current_section_start:
            self.current_section_end = self.current_time
            self.mark_end_button.setStyleSheet("background-color: #FF4444;")
            self.mark_start_button.setStyleSheet("")
            self.update_selection_label()
            self.add_section_button.setEnabled(True)
            self.status_label.setText("End point marked. Click 'Add Section' to add this section")
        else:
            self.status_label.setText("Error: End point must be after start point!")

    def update_selection_label(self):
        if self.current_section_start is not None:
            start_min, start_sec = divmod(int(self.current_section_start), 60)
            if self.current_section_end is not None:
                end_min, end_sec = divmod(int(self.current_section_end), 60)
                self.selection_label.setText(
                    f"Selected: {start_min:02}:{start_sec:02} to {end_min:02}:{end_sec:02}"
                )
            else:
                self.selection_label.setText(
                    f"Start: {start_min:02}:{start_sec:02} - Click 'Mark End' to set end point"
                )
        else:
            self.selection_label.setText("No section selected")

    def add_section(self):
        if self.current_section_start is None or self.current_section_end is None:
            self.status_label.setText("Error: Please select both start and end points!")
            return
            
        self.sections.append((self.current_section_start, self.current_section_end))
        start_min, start_sec = divmod(int(self.current_section_start), 60)
        end_min, end_sec = divmod(int(self.current_section_end), 60)
        self.section_list_widget.addItem(
            f"Section {len(self.sections)}: {start_min:02}:{start_sec:02} to {end_min:02}:{end_sec:02}"
        )
        
        # Reset selection
        self.current_section_start = None
        self.current_section_end = None
        self.add_section_button.setEnabled(False)
        # Reset button styles
        self.mark_start_button.setStyleSheet("")
        self.mark_end_button.setStyleSheet("")
        self.update_selection_label()
        self.status_label.setText(f"Section {len(self.sections)} added")

    def delete_section(self):
        selected_item = self.section_list_widget.currentItem()
        if selected_item:
            section_text = selected_item.text()
            section_idx = int(section_text.split(":")[0].split()[1]) - 1
            
            # Remove the section from the list
            self.sections.pop(section_idx)
            
            # Update the section list display
            self.section_list_widget.takeItem(self.section_list_widget.row(selected_item))
            
            # Re-number the sections in the list widget with MM:SS format
            for i in range(self.section_list_widget.count()):
                item = self.section_list_widget.item(i)
                start_min, start_sec = divmod(int(self.sections[i][0]), 60)
                end_min, end_sec = divmod(int(self.sections[i][1]), 60)
                item.setText(
                    f"Section {i + 1}: {start_min:02}:{start_sec:02} to {end_min:02}:{end_sec:02}"
                )
            
            self.status_label.setText(f"Section {section_idx + 1} deleted.")

    def process_sections(self):
        if not self.sections:
            self.status_label.setText("Error: No sections to process!")
            return

        if self.song is None:
            self.status_label.setText("Error: No song loaded!")
            return

        self.audio_processor = AudioProcessor(self.song, self.sections)
        self.audio_processor.status_update.connect(self.update_status)
        self.audio_processor.start()

    def update_status(self, message):
        self.status_label.setText(message)

    def closeEvent(self, event):
        if self.audio_processor and self.audio_processor.isRunning():
            self.audio_processor.terminate()  # Terminate the thread if it's running
        event.accept()  # Close the application

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = resources.get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    
    apply_dark_mode(app)
    window = AudioApp()
    window.show()
    sys.exit(app.exec_())
