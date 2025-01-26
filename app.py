import os
import vlc
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
    QFileDialog,
    QShortcut
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QTime
from PyQt5.QtGui import QIcon, QKeySequence
import resources
import datetime

# Add VLC to system path
if sys.platform.startswith('win32'):
    # Try common VLC installation paths
    vlc_paths = [
        os.path.join(os.environ.get('PROGRAMFILES'), 'VideoLAN', 'VLC'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)'), 'VideoLAN', 'VLC'),
        r'C:\Program Files\VideoLAN\VLC',
        r'C:\Program Files (x86)\VideoLAN\VLC'
    ]
    
    for vlc_path in vlc_paths:
        if os.path.exists(vlc_path):
            if vlc_path not in os.environ['PATH']:
                os.environ['PATH'] = vlc_path + ';' + os.environ['PATH']
            break
    else:
        print("Warning: VLC installation not found. Please install VLC media player.")

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

def format_time(seconds):
    """Helper function to format time in MM:SS format"""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02}:{secs:02}"

class AudioProcessor(QThread):
    status_update = pyqtSignal(str)

    def __init__(self, song, sections, song_path):
        super().__init__()
        self.song = song
        self.sections = sections
        self.song_path = song_path

    def run(self):
        # Get original filename without extension
        base_filename = os.path.splitext(os.path.basename(self.song_path))[0]
        # Create timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Combine filename and timestamp for output directory
        output_dir = os.path.join("output", f"{base_filename}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)

        # Create info text file
        info_path = os.path.join(output_dir, "section_info.txt")
        with open(info_path, "w") as f:
            f.write("Vocal Removal Sections:\n\n")
            for idx, (start_time, end_time) in enumerate(self.sections, 1):
                f.write(f"Section {idx}: {format_time(start_time)} to {format_time(end_time)}\n")
            f.write(f"\nOriginal file: {os.path.basename(self.song_path)}\n")
            f.write(f"Processed on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

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
        # Update the export path
        output_path = os.path.join(output_dir, "output.mp3")
        combined.export(output_path, format="mp3")

        self.status_update.emit("Cleaning up temporary files...")
        # Clean up temporary files
        os.remove("temp_section.wav")
        shutil.rmtree("separated", ignore_errors=True)
        self.status_update.emit(f"Processing complete! Output saved in: {output_dir}")

class AudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window icon
        icon_path = resources.get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        # Initialize VLC instance and player with logging disabled
        self.instance = vlc.Instance('--quiet')  # Add quiet flag
        self.player = self.instance.media_player_new()
        self.media = None
        
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
        
        # Setup timer for updating position
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)  # Update every 100ms
        self.update_timer.timeout.connect(self.update_time)
        
        # Remove focus from all buttons
        for button in self.findChildren(QPushButton):
            button.setFocusPolicy(Qt.NoFocus)
        
        # Initialize keyboard shortcuts
        self.setup_shortcuts()

        # Add highlight color as class variable
        self.highlight_color = "background-color: #FF4444;"
        self.default_color = ""
        
        # Initialize with mark start highlighted
        self.mark_start_button.setStyleSheet(self.highlight_color)

        # Initialize with both buttons disabled
        self.add_section_button.setEnabled(False)
        self.process_button.setEnabled(False)  # Initially disabled

        # Add rate limiting for seeking
        self.last_seek_time = 0
        self.seek_cooldown = 50  # Minimum milliseconds between seeks

        # Add debounce timer for seeking
        self.seek_timer = QTimer()
        self.seek_timer.setSingleShot(True)
        self.seek_timer.timeout.connect(self.perform_seek)
        self.pending_seek_position = None

        self.was_playing = False  # Add this to track playback state

        # Initialize time display with whole seconds only
        self.time_display.setText("00:00 / 00:00")

    def initUI(self):
        self.setWindowTitle("Audio Section Editor")
        self.setGeometry(300, 300, 500, 600)

        # Main layout
        main_layout = QVBoxLayout()

        # Top row with Load Song and Playback Controls
        top_row = QHBoxLayout()
        
        # Song loading section
        song_group = QGroupBox("Load Song")
        song_layout = QVBoxLayout()
        self.load_button = QPushButton(" Import File")
        self.load_button.setIcon(self.style().standardIcon(QPushButton().style().SP_DirOpenIcon))
        self.load_button.clicked.connect(self.load_song)
        self.load_button.setMinimumWidth(200)  # Make button wider
        song_layout.addWidget(self.load_button, alignment=Qt.AlignCenter)  # Center the button
        song_group.setLayout(song_layout)
        top_row.addWidget(song_group, 1)  # Add stretch factor of 1
        
        # Playback controls
        playback_group = QGroupBox("Playback Controls")
        playback_layout = QHBoxLayout()
        
        # Play button
        self.play_button = QPushButton("Play")
        self.play_button.setIcon(self.style().standardIcon(QPushButton().style().SP_MediaPlay))
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setFixedWidth(100)
        playback_layout.addWidget(self.play_button)
        
        # Volume controls
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(5)
        
        volume_label = QLabel("🔊")
        volume_layout.addWidget(volume_label)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.setTickInterval(25)
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_percentage = QLabel("50%")
        self.volume_percentage.setFixedWidth(40)
        volume_layout.addWidget(self.volume_percentage)
        
        playback_layout.addLayout(volume_layout)
        playback_layout.addStretch()
        
        playback_group.setLayout(playback_layout)
        top_row.addWidget(playback_group, 2)  # Add stretch factor of 2
        
        # Add top row to main layout
        main_layout.addLayout(top_row)

        # Timeline and volume layout
        timeline_volume_row = QHBoxLayout()
        
        # Timeline group
        timeline_group = QGroupBox("Timeline")
        timeline_layout = QVBoxLayout()
        
        # Add song name label
        self.song_label = QLabel("No song loaded")
        self.song_label.setStyleSheet("color: gray; font-style: italic;")
        self.song_label.setAlignment(Qt.AlignCenter)  # Center the text
        timeline_layout.addWidget(self.song_label)
        
        # Add time display label
        self.time_display = QLabel("00:00.0 / 00:00.0")
        timeline_layout.addWidget(self.time_display)
        
        # Timeline slider
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setRange(0, 100)
        self.timeline_slider.valueChanged.connect(self.on_slider_change)
        timeline_layout.addWidget(self.timeline_slider)
        
        # Fine control buttons - more subtle design
        fine_control_layout = QHBoxLayout()
        fine_control_layout.setSpacing(4)
        
        back_01_button = QPushButton("←")
        back_01_button.clicked.connect(lambda: self.adjust_time(-1.0))
        back_01_button.setFixedWidth(24)
        back_01_button.setFixedHeight(24)
        back_01_button.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                padding: 0px;
                background-color: #3E3E3E;
            }
        """)
        
        # Update label to show 1s increment
        time_increment_label = QLabel("1s")
        time_increment_label.setStyleSheet("font-size: 10px; color: #888888;")
        time_increment_label.setAlignment(Qt.AlignCenter)
        
        forward_01_button = QPushButton("→")
        forward_01_button.clicked.connect(lambda: self.adjust_time(1.0))
        forward_01_button.setFixedWidth(24)
        forward_01_button.setFixedHeight(24)
        forward_01_button.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                padding: 0px;
                background-color: #3E3E3E;
            }
        """)
        
        # Center the controls with stretches
        fine_control_layout.addStretch()
        fine_control_layout.addWidget(back_01_button)
        fine_control_layout.addWidget(time_increment_label)
        fine_control_layout.addWidget(forward_01_button)
        fine_control_layout.addStretch()
        
        timeline_layout.addLayout(fine_control_layout)
        
        timeline_group.setLayout(timeline_layout)
        timeline_volume_row.addWidget(timeline_group)
        
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
        
        # Add section and cancel buttons in a horizontal layout
        section_buttons_layout = QHBoxLayout()
        
        self.add_section_button = QPushButton("Add Section")
        self.add_section_button.clicked.connect(self.add_section)
        self.add_section_button.setEnabled(False)  # Disabled until a valid selection is made
        section_buttons_layout.addWidget(self.add_section_button)
        
        self.cancel_section_button = QPushButton("Cancel")
        self.cancel_section_button.clicked.connect(self.cancel_section)
        self.cancel_section_button.setEnabled(False)  # Disabled until marking starts
        section_buttons_layout.addWidget(self.cancel_section_button)
        
        section_layout.addLayout(section_buttons_layout)
        
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
        self.process_button.setObjectName("process_button")
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
            min-height: 30px;  /* Fixed minimum height */
            max-height: 30px;  /* Fixed maximum height */
        """)
        self.status_label.setWordWrap(True)  # Enable text wrapping
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # Align text left and vertically center
        main_layout.addWidget(self.status_label)

        # Apply main layout
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Apply stylesheet for modern look
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2E2E2E;
            }
            QPushButton {
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
                outline: none;
                background-color: #444444;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:disabled {
                background-color: #2E2E2E;
                color: #666666;
                border: 1px solid #444444;
            }
            QPushButton#process_button {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton#process_button:hover {
                background-color: #45a049;
            }
            QPushButton#process_button:disabled {
                background-color: #2E2E2E;
                color: #666666;
                border: 1px solid #444444;
                font-weight: normal;
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
            try:
                self.status_label.setText("Creating working copy...")
                
                # Create temp directory if it doesn't exist
                os.makedirs('temp', exist_ok=True)
                
                # Create a temporary copy with original extension
                file_ext = os.path.splitext(file)[1]
                self.temp_file = os.path.join('temp', f'working_copy{file_ext}')
                shutil.copy2(file, self.temp_file)
                
                # Load the temp file using VLC first (for playback)
                self.media = self.instance.media_new(self.temp_file)
                self.player.set_media(self.media)
                
                # Then load with pydub (for processing)
                try:
                    self.song = AudioSegment.from_file(self.temp_file)
                except Exception as e:
                    # If mp3 fails, try forcing the format
                    if file.lower().endswith('.mp3'):
                        self.song = AudioSegment.from_file(self.temp_file, format="mp3", codec="mp3")
                    else:
                        raise e
                
                self.song_path = file  # Keep original path for reference
                # Show filename with extension
                filename = os.path.basename(self.song_path)
                self.song_label.setText(filename)
                self.song_label.setStyleSheet("color: #FFFFFF; font-style: normal;")
                self.status_label.setText("Loading song, please wait...")
                
                # Disable controls during loading
                self.timeline_slider.setEnabled(False)
                self.play_button.setEnabled(False)

                # Calculate the song length using AudioSegment
                self.song_length = len(self.song) / 1000  # Convert milliseconds to seconds
                self.timeline_slider.setRange(0, int(self.song_length))  # Use whole seconds
                self.current_time = 0
                
                # Add artificial delay for proper initialization
                QTimer.singleShot(500, self._start_initialization)
                
            except Exception as e:
                self.status_label.setText(f"Error loading song: {str(e)}")
                self.song = None
                self.song_path = None
                if hasattr(self, 'temp_file') and os.path.exists(self.temp_file):
                    try:
                        os.remove(self.temp_file)
                    except:
                        pass

    def _start_initialization(self):
        # Play and immediately pause to initialize the media
        self.player.play()
        QTimer.singleShot(200, self._pause_and_initialize)

    def _pause_and_initialize(self):
        self.player.pause()
        # Get media length and ensure it's loaded
        length = self.player.get_length()
        if length > 0:
            self.player.set_time(0)
            self.current_time = 0
            self.timeline_slider.setValue(0)
            self.update_time_display(0)
            self.is_playing = False
            self.play_button.setText("Play")
            
            # Set and sync initial volume
            initial_volume = self.volume_slider.value()
            self.player.audio_set_volume(initial_volume)
            self.volume_percentage.setText(f"{initial_volume}%")
            
            # Re-enable controls
            self.timeline_slider.setEnabled(True)
            self.play_button.setEnabled(True)
            self.status_label.setText("Song loaded successfully!")
        else:
            # If media isn't loaded yet, try again
            QTimer.singleShot(100, self._pause_and_initialize)

    def toggle_play(self):
        if self.song is None:
            self.status_label.setText("Error: No song loaded!")
            return

        if self.is_playing:
            self.player.pause()
            self.play_button.setText("Play")
            self.update_timer.stop()
            # Ensure current time is synchronized when pausing
            current_ms = self.player.get_time()
            if current_ms >= 0:
                self.current_time = current_ms / 1000.0
                self.timeline_slider.setValue(int(self.current_time))
                self.update_time_display(self.current_time)
        else:
            self.player.play()
            self.play_button.setText("Pause")
            self.update_timer.start()
        self.is_playing = not self.is_playing

    def update_time(self):
        if self.is_playing and self.player.is_playing():
            # Get current time in milliseconds
            current_ms = self.player.get_time()
            if current_ms >= 0:
                self.current_time = current_ms / 1000.0
                # Update slider position without triggering valueChanged signal
                self.timeline_slider.blockSignals(True)
                self.timeline_slider.setValue(int(self.current_time))  # Convert to whole seconds
                self.timeline_slider.blockSignals(False)
                self.update_time_display(self.current_time)
                
                # Check if we've reached the end of the song
                if current_ms >= self.player.get_length():
                    self.stop_audio()
                    return
        else:
            if self.is_playing:  # If the song has finished
                self.stop_audio()
            else:
                self.update_timer.stop()
                self.play_button.setText("Play")

    def update_time_display(self, current_time):
        if not self.song:
            self.time_display.setText("00:00 / 00:00")
            return
        
        # Format current time in whole seconds
        minutes = int(current_time) // 60
        seconds = int(current_time) % 60
        
        # Format total time
        total_minutes = int(self.song_length) // 60
        total_seconds = int(self.song_length) % 60
        
        self.time_display.setText(
            f"{minutes:02}:{seconds:02} / {total_minutes:02}:{total_seconds:02}"
        )

    def on_slider_change(self):
        if not self.song:  # Check if song is loaded
            return
        
        # Store playback state and pause if playing
        if self.is_playing:
            self.was_playing = True
            self.is_playing = False
            self.play_button.setText("Play")
            self.update_timer.stop()
            self.player.pause()
        
        # Store the desired position
        self.pending_seek_position = self.timeline_slider.value()
        
        # Reset and start the debounce timer
        self.seek_timer.stop()
        self.seek_timer.start(50)  # 50ms debounce

    def perform_seek(self):
        if self.pending_seek_position is None:
            return
        
        # Get the final position we want to seek to
        new_time = self.pending_seek_position
        self.current_time = new_time
        
        if self.player.get_length() > 0:
            # Just seek since we're already paused
            position = new_time / self.song_length
            self.player.set_position(float(position))
            
            # Resume playback if it was playing before
            if self.was_playing:
                QTimer.singleShot(100, self.resume_playback)
            
        self.update_time_display(self.current_time)
        self.pending_seek_position = None

    def resume_playback(self):
        self.player.play()
        self.is_playing = True
        self.was_playing = False
        self.play_button.setText("Pause")
        self.update_timer.start()

    def set_volume(self):
        volume = self.volume_slider.value()
        self.player.audio_set_volume(volume)
        self.volume_percentage.setText(f"{volume}%")

    def start_selection(self):
        if not self.song:
            self.status_label.setText("Error: No song loaded!")
            return
        
        # Use current timeline position immediately
        self.current_section_start = self.current_time
        # Update button highlighting
        self.mark_start_button.setStyleSheet(self.default_color)
        self.mark_end_button.setStyleSheet(self.highlight_color)
        self.add_section_button.setStyleSheet(self.default_color)
        self.cancel_section_button.setEnabled(True)  # Enable cancel button
        self.update_selection_label()

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
            # Update button highlighting
            self.mark_end_button.setStyleSheet(self.default_color)
            self.mark_start_button.setStyleSheet(self.default_color)
            self.add_section_button.setStyleSheet(self.highlight_color)
            self.update_selection_label()
            self.add_section_button.setEnabled(True)
        else:
            self.status_label.setText("Error: End point must be after start point!")

    def update_selection_label(self):
        if self.current_section_start is not None:
            start_min = int(self.current_section_start) // 60
            start_sec = int(self.current_section_start) % 60
            
            if self.current_section_end is not None:
                end_min = int(self.current_section_end) // 60
                end_sec = int(self.current_section_end) % 60
                
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
        
        start_min = int(self.current_section_start) // 60
        start_sec = int(self.current_section_start) % 60
        end_min = int(self.current_section_end) // 60
        end_sec = int(self.current_section_end) % 60
        
        self.section_list_widget.addItem(
            f"Section {len(self.sections)}: {start_min:02}:{start_sec:02} to {end_min:02}:{end_sec:02}"
        )
        
        # Enable process button when we have sections
        self.process_button.setEnabled(True)
        
        # Reset selection and buttons
        self.current_section_start = None
        self.current_section_end = None
        self.add_section_button.setEnabled(False)
        self.cancel_section_button.setEnabled(False)  # Disable cancel button
        # Reset button styles and highlight mark start for next section
        self.mark_start_button.setStyleSheet(self.highlight_color)
        self.mark_end_button.setStyleSheet(self.default_color)
        self.add_section_button.setStyleSheet(self.default_color)
        self.status_label.setText(f"Section {len(self.sections)} added successfully")

    def delete_section(self):
        selected_item = self.section_list_widget.currentItem()
        if selected_item:
            section_text = selected_item.text()
            section_idx = int(section_text.split(":")[0].split()[1]) - 1
            
            # Remove the section from the list
            self.sections.pop(section_idx)
            
            # Update the section list display
            self.section_list_widget.takeItem(self.section_list_widget.row(selected_item))
            
            # Re-number the sections in the list widget with whole seconds
            for i in range(self.section_list_widget.count()):
                item = self.section_list_widget.item(i)
                
                # Format start time with whole seconds
                start_min = int(self.sections[i][0]) // 60
                start_sec = int(self.sections[i][0]) % 60
                
                # Format end time with whole seconds
                end_min = int(self.sections[i][1]) // 60
                end_sec = int(self.sections[i][1]) % 60
                
                item.setText(
                    f"Section {i + 1}: {start_min:02}:{start_sec:02} to {end_min:02}:{end_sec:02}"
                )
            
            # Disable process button if no sections remain
            if len(self.sections) == 0:
                self.process_button.setEnabled(False)
            
            self.status_label.setText(f"Section {section_idx + 1} deleted.")

    def process_sections(self):
        if not self.sections:
            self.status_label.setText("Error: No sections to process!")
            return

        if self.song is None:
            self.status_label.setText("Error: No song loaded!")
            return

        self.audio_processor = AudioProcessor(self.song, self.sections, self.song_path)
        self.audio_processor.status_update.connect(self.update_status)
        self.audio_processor.start()

    def update_status(self, message):
        self.status_label.setText(message)

    def closeEvent(self, event):
        # Stop update timer first
        self.update_timer.stop()
        
        # Stop playback and reset state
        if hasattr(self, 'is_playing'):
            self.is_playing = False
        
        # Release VLC resources in a safe order
        if hasattr(self, 'player'):
            if self.player:
                self.player.stop()
                # Small delay to ensure stop completes
                QTimer.singleShot(100, self._finish_cleanup)
                event.ignore()  # Don't accept the event yet
                return
            
        # If no player exists, just cleanup and close
        self._finish_cleanup()
        event.accept()

    def _finish_cleanup(self):
        # Release VLC resources
        if hasattr(self, 'player') and self.player:
            self.player.release()
            self.player = None
        
        if hasattr(self, 'instance') and self.instance:
            self.instance.release()
            self.instance = None
        
        # Stop audio processor if running
        if self.audio_processor and self.audio_processor.isRunning():
            self.audio_processor.terminate()
        
        # Clean up temporary file
        if hasattr(self, 'temp_file') and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except:
                pass
        
        # Clean up temp directory if empty
        try:
            os.rmdir('temp')
        except:
            pass
        
        # Now we can safely close the application
        QApplication.quit()

    def adjust_time(self, delta):
        if not self.song:
            return
            
        # Rate limiting for seeking operations
        current_time = QTime.currentTime().msecsSinceStartOfDay()
        if current_time - self.last_seek_time < self.seek_cooldown:
            return
        self.last_seek_time = current_time
            
        # Calculate new time
        new_time = round(self.current_time + delta, 1)
        new_time = max(0, min(new_time, self.song_length))
        
        # Store current playing state but don't resume after
        was_playing = self.is_playing
        if was_playing:
            self.is_playing = False
            self.play_button.setText("Play")
            self.update_timer.stop()
            self.player.pause()
        
        # Set the new position directly without using the debounce mechanism
        self.current_time = new_time
        self.timeline_slider.setValue(int(new_time))
        if self.player.get_length() > 0:
            position = new_time / self.song_length
            self.player.set_position(float(position))
        self.update_time_display(new_time)

    def setup_shortcuts(self):
        # Space bar for play/pause
        self.play_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.play_shortcut.activated.connect(self.toggle_play)
        
        # Left/Right arrow keys for time adjustment (1 second)
        self.left_shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.left_shortcut.activated.connect(lambda: self.adjust_time(-1.0))
        
        self.right_shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.right_shortcut.activated.connect(lambda: self.adjust_time(1.0))
        
        # Up/Down arrow keys for volume control
        self.up_shortcut = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.up_shortcut.activated.connect(lambda: self.adjust_volume(5))  # Increase by 5%
        
        self.down_shortcut = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.down_shortcut.activated.connect(lambda: self.adjust_volume(-5))  # Decrease by 5%
        
        # Enter key for section marking
        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.enter_shortcut.activated.connect(self.handle_enter)

    def adjust_volume(self, delta):
        new_volume = min(100, max(0, self.volume_slider.value() + delta))
        self.volume_slider.setValue(new_volume)

    def handle_enter(self):
        if not self.song:
            self.status_label.setText("Error: No song loaded!")
            return
        
        # If no start point is set, set start point
        if self.current_section_start is None:
            self.start_selection()
            # Highlight mark end button
            self.mark_start_button.setStyleSheet(self.default_color)
            self.mark_end_button.setStyleSheet(self.highlight_color)
            self.add_section_button.setStyleSheet(self.default_color)
        
        # If start is set but no end point, set end point
        elif self.current_section_end is None:
            self.end_selection()
            if self.add_section_button.isEnabled():  # Only if end point was valid
                self.mark_end_button.setStyleSheet(self.default_color)
                self.add_section_button.setStyleSheet(self.highlight_color)
        
        # If both points are set, add the section
        elif self.add_section_button.isEnabled():
            self.add_section()
            # Reset to start state - highlight mark start
            self.mark_start_button.setStyleSheet(self.highlight_color)
            self.mark_end_button.setStyleSheet(self.default_color)
            self.add_section_button.setStyleSheet(self.default_color)

    def stop_audio(self):
        self.player.pause()
        self.is_playing = False
        self.play_button.setText("Play")
        self.update_timer.stop()
        # Reset position to start
        self.current_time = 0
        self.timeline_slider.setValue(0)
        self.update_time_display(0)

    def cancel_section(self):
        # Reset selection
        self.current_section_start = None
        self.current_section_end = None
        
        # Reset button states
        self.add_section_button.setEnabled(False)
        self.cancel_section_button.setEnabled(False)
        
        # Reset button styles and highlight mark start
        self.mark_start_button.setStyleSheet(self.highlight_color)
        self.mark_end_button.setStyleSheet(self.default_color)
        self.add_section_button.setStyleSheet(self.default_color)
        
        # Update the selection label
        self.update_selection_label()
        self.status_label.setText("Section marking cancelled")

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
