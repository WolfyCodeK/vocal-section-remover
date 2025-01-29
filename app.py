import os
import sys
from pydub import AudioSegment
from PyQt6.QtWidgets import (
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
    QStyle,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QTime, QUrl
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut, QPixmap, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import resources
import datetime
from demucs.pretrained import get_model
from demucs.apply import apply_model
from demucs.audio import AudioFile
import torchaudio

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
    # Update QSlider styles for PyQt6
    dark_stylesheet = dark_stylesheet.replace(
        "QSlider::handle:horizontal {",
        "QSlider::handle:horizontal {"
    )
    app.setStyleSheet(dark_stylesheet)

def format_time(seconds):
    """Helper function to format time in MM:SS format"""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02}:{secs:02}"

def format_time_precise(seconds):
    """Helper function to format time with decimal precision"""
    minutes = int(seconds) // 60
    secs = seconds % 60
    
    # Check if seconds is effectively a whole number
    if abs(secs - round(secs)) < 0.001:  # If very close to a whole number
        return f"{minutes:02}:{int(secs):02}"
    else:
        # Format with exactly 2 decimal places
        return f"{minutes:02}:{secs:05.2f}"

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

        # Load the model once
        self.status_update.emit("Loading Demucs model...")
        model = get_model('htdemucs')
        model.eval()
        
        # Sort sections by start time to ensure they are processed in order
        self.sections.sort(key=lambda x: x[0])

        combined = AudioSegment.empty()  # Start with an empty audio segment
        last_end_time = 0  # Keep track of the last section's end time

        for idx, (start_time, end_time) in enumerate(self.sections, start=1):
            start_formatted = format_time_precise(start_time)
            end_formatted = format_time_precise(end_time)
            self.status_update.emit(f"Section {idx} processing from {start_formatted} to {end_formatted}...")
            section = self.song[start_time * 1000:end_time * 1000]
            section.export("temp_section.wav", format="wav")

            # Use AudioFile to load the audio
            audio_file = AudioFile("temp_section.wav")
            wav = audio_file.read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
            ref = wav.mean(0)
            wav = (wav - ref.mean()) / ref.std()
            
            sources = apply_model(model, wav[None], device='cpu', progress=True, num_workers=1)[0]
            sources = sources * ref.std() + ref.mean()
            
            # Mix all stems except vocals to create instrumental
            # sources order is: [drums, bass, other, vocals]
            drums = sources[0]
            bass = sources[1]
            other = sources[2]
            # Combine all stems except vocals
            instrumental = drums + bass + other
            
            # Save audio using torchaudio
            torchaudio.save(
                "temp_section_no_vocals.wav",
                instrumental.cpu(),
                sample_rate=int(model.samplerate)
            )

            # Load the processed instrumental track
            instrumental = AudioSegment.from_file("temp_section_no_vocals.wav")

            self.status_update.emit(f"Adding song parts for section {idx}...")
            # Add the part before the section if necessary
            if start_time > last_end_time:
                part_before_section = self.song[last_end_time * 1000:start_time * 1000]
                combined += part_before_section

            # First add the section with vocals (original)
            section_with_vocals = section
            combined += section_with_vocals

            # Then add the same section without vocals (instrumental)
            combined += instrumental

            last_end_time = end_time  # Update the last end time

        # Add the remaining part of the song after the last section
        if last_end_time < len(self.song) / 1000:
            remaining_part = self.song[last_end_time * 1000:]
            combined += remaining_part

        self.status_update.emit("Exporting final result...")
        # Export the final result
        output_path = os.path.join(output_dir, "output.mp3")
        combined.export(output_path, format="mp3")

        self.status_update.emit("Cleaning up temporary files...")
        # Clean up temporary files
        try:
            os.remove("temp_section.wav")
            os.remove("temp_section_no_vocals.wav")
        except:
            pass

        self.status_update.emit(f"Processing complete! Output saved in: {output_dir}")

class AudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window icon
        icon_path = resources.get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        # Initialize QMediaPlayer instead of VLC
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Set initial volume (50%)
        self.audio_output.setVolume(0.5)  # QAudioOutput uses 0-1 range
        
        # Connect position and duration signals
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        
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
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
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

        # Initialize time display with proper decimal places
        self.time_display.setText("00:00.00 / 00:00.00")

    def create_white_icon(self, standard_icon):
        # Get the icon and convert to pixmap
        icon = self.style().standardIcon(standard_icon)
        pixmap = icon.pixmap(16, 16)
        
        # Create a new image in ARGB32 format
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        
        # Convert to white
        for x in range(image.width()):
            for y in range(image.height()):
                color = image.pixelColor(x, y)
                if color.alpha() > 0:  # If pixel is not transparent
                    color.setRed(255)
                    color.setGreen(255)
                    color.setBlue(255)
                    image.setPixelColor(x, y, color)
        
        return QIcon(QPixmap.fromImage(image))

    def initUI(self):
        # Add constant for button height at the start of initUI
        BUTTON_HEIGHT = 35  # Standard height for all buttons

        # Set minimum window size instead of fixed
        self.setMinimumWidth(500)
        self.setMinimumHeight(750)  # Increased minimum height to ensure all elements are visible
        self.resize(500, 750)  # Initial size matches minimum
        self.setWindowTitle("Voice Section Remover")
        
        # Main layout with expanding margins
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Top row with Load Song and Volume Controls
        top_row = QHBoxLayout()
        
        # Song loading section
        song_group = QGroupBox("Load Song")
        song_layout = QVBoxLayout()
        self.load_button = QPushButton(" Import File")
        self.load_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.load_button.clicked.connect(self.load_song)
        self.load_button.setMinimumWidth(200)
        self.load_button.setFixedHeight(BUTTON_HEIGHT)  # Set fixed height
        song_layout.addWidget(self.load_button, alignment=Qt.AlignmentFlag.AlignCenter)
        song_group.setLayout(song_layout)
        top_row.addWidget(song_group)
        
        # Volume controls
        volume_group = QGroupBox("Volume")
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(10)  # Increased spacing between elements
        volume_layout.setContentsMargins(25, 0, -5, 5)  # Reduced vertical margins, increased horizontal
        
        # Volume icon
        volume_label = QLabel("🔊")
        volume_layout.addWidget(volume_label)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.volume_slider.setTickInterval(25)
        volume_layout.addWidget(self.volume_slider, stretch=1)
        
        # Percentage label
        self.volume_percentage = QLabel("50%")
        self.volume_percentage.setFixedWidth(40)
        volume_layout.addWidget(self.volume_percentage)
        
        volume_group.setLayout(volume_layout)
        top_row.addWidget(volume_group, stretch=1)  # Add stretch factor
        
        # Add top row to main layout
        main_layout.addLayout(top_row)

        # Timeline group
        timeline_group = QGroupBox("Timeline")
        timeline_layout = QVBoxLayout()
        timeline_layout.setSpacing(8)  # Increased spacing between elements
        timeline_layout.setContentsMargins(10, 5, 10, 10)  # Increased bottom margin
        
        # Add song name label with reduced height
        self.song_label = QLabel("No song loaded")
        self.song_label.setStyleSheet("""
            color: gray;
            font-style: italic;
            padding: 2px;
        """)
        self.song_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_label.setMinimumHeight(25)
        self.song_label.setWordWrap(True)
        self.song_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        timeline_layout.addWidget(self.song_label)
        
        # Time display with added spacing
        self.time_display = QLabel("00:00.00 / 00:00.00")
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timeline_layout.addWidget(self.time_display)
        
        # Add spacing before timeline slider
        timeline_layout.addSpacing(5)
        
        # Timeline slider - multiply range by 100 to handle 2 decimal places
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 0)  # Will be set when song loads
        self.timeline_slider.valueChanged.connect(self.on_slider_change)
        self.timeline_slider.sliderReleased.connect(self.on_slider_released)
        timeline_layout.addWidget(self.timeline_slider)
        
        # Add spacing after timeline slider
        timeline_layout.addSpacing(5)
        
        # Fine control and play buttons - more subtle design
        control_layout = QHBoxLayout()
        control_layout.setSpacing(4)
        control_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Back button
        back_01_button = QPushButton()
        back_01_button.clicked.connect(lambda: self.adjust_time(-1.0))
        back_01_button.setFixedWidth(24)
        back_01_button.setFixedHeight(24)
        back_01_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        back_01_button.setStyleSheet("""
            QPushButton {
                padding: 0px;
                background-color: #3E3E3E;
            }
            QPushButton:hover {
                background-color: #4E4E4E;
            }
        """)
        
        # Play button (icon only)
        self.play_button = QPushButton()
        self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setFixedWidth(24)
        self.play_button.setFixedHeight(24)
        self.play_button.setStyleSheet("""
            QPushButton {
                padding: 0px;
                background-color: #3E3E3E;
            }
            QPushButton:hover {
                background-color: #4E4E4E;
            }
        """)
        
        # Forward button
        forward_01_button = QPushButton()
        forward_01_button.clicked.connect(lambda: self.adjust_time(1.0))
        forward_01_button.setFixedWidth(24)
        forward_01_button.setFixedHeight(24)
        forward_01_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaSkipForward))
        forward_01_button.setStyleSheet("""
            QPushButton {
                padding: 0px;
                background-color: #3E3E3E;
            }
            QPushButton:hover {
                background-color: #4E4E4E;
            }
        """)

        # Center the controls with stretches
        control_layout.addStretch()
        control_layout.addWidget(back_01_button)
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(forward_01_button)
        control_layout.addStretch()
        
        timeline_layout.addLayout(control_layout)
        
        timeline_group.setLayout(timeline_layout)
        main_layout.addWidget(timeline_group)

        # Section controls
        section_group = QGroupBox("Sections")
        section_layout = QVBoxLayout()
        section_layout.setSpacing(10)
        
        # Top buttons section (fixed height)
        top_section = QWidget()
        top_section.setFixedHeight(120)  # Fixed height for buttons
        top_section_layout = QVBoxLayout(top_section)
        top_section_layout.setSpacing(5)
        top_section_layout.setContentsMargins(0, 0, 0, 0)
        
        # Timeline selection buttons
        selection_buttons_layout = QHBoxLayout()
        self.mark_start_button = QPushButton("Mark Start")
        self.mark_start_button.clicked.connect(self.start_selection)
        self.mark_start_button.setFixedHeight(BUTTON_HEIGHT)
        self.mark_end_button = QPushButton("Mark End")
        self.mark_end_button.clicked.connect(self.end_selection)
        self.mark_end_button.setFixedHeight(BUTTON_HEIGHT)
        selection_buttons_layout.addWidget(self.mark_start_button)
        selection_buttons_layout.addWidget(self.mark_end_button)
        top_section_layout.addLayout(selection_buttons_layout)
        
        # Current selection display
        self.selection_label = QLabel("No section selected")
        self.selection_label.setStyleSheet("color: #00B4FF;")
        self.selection_label.setFixedHeight(25)
        top_section_layout.addWidget(self.selection_label)
        
        # Add section and cancel buttons
        section_buttons_layout = QHBoxLayout()
        self.add_section_button = QPushButton("Add Section")
        self.add_section_button.clicked.connect(self.add_section)
        self.add_section_button.setEnabled(False)
        self.add_section_button.setFixedHeight(BUTTON_HEIGHT)
        section_buttons_layout.addWidget(self.add_section_button)
        
        self.cancel_section_button = QPushButton("Cancel")
        self.cancel_section_button.clicked.connect(self.cancel_section)
        self.cancel_section_button.setEnabled(False)
        self.cancel_section_button.setFixedHeight(BUTTON_HEIGHT)
        section_buttons_layout.addWidget(self.cancel_section_button)
        top_section_layout.addLayout(section_buttons_layout)
        
        # Add the fixed-height top section
        section_layout.addWidget(top_section)
        
        # Section list (with minimum height)
        self.section_list_widget = QListWidget()
        self.section_list_widget.setMinimumHeight(60)  # Reduced from 100 to 60
        self.section_list_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        section_layout.addWidget(self.section_list_widget, stretch=1)
        
        # Delete section button (fixed height)
        self.delete_section_button = QPushButton("Delete Selected Section")
        self.delete_section_button.clicked.connect(self.delete_section)
        self.delete_section_button.setFixedHeight(BUTTON_HEIGHT)
        section_layout.addWidget(self.delete_section_button)
        
        section_group.setLayout(section_layout)
        main_layout.addWidget(section_group, stretch=1)

        # Process button
        self.process_button = QPushButton("Process Sections")
        self.process_button.setObjectName("process_button")
        self.process_button.clicked.connect(self.process_sections)
        self.process_button.setFixedHeight(BUTTON_HEIGHT)
        main_layout.addWidget(self.process_button)

        # Status label with default style for info messages
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            color: #3498db;
            font-size: 14px;
            font-weight: bold;
            padding: 2px;
        """)
        self.status_label.setMinimumHeight(30)
        self.status_label.setWordWrap(True)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
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
                self.update_status("Loading song...")
                
                # Stop current playback and reset state
                if self.is_playing:
                    self.player.stop()
                    self.is_playing = False
                    self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPlay))
                    self.update_timer.stop()

                # Reset all sections and UI elements
                self.sections = []
                self.section_list_widget.clear()
                self.current_section_start = None
                self.current_section_end = None
                self.process_button.setEnabled(False)
                self.add_section_button.setEnabled(False)
                self.cancel_section_button.setEnabled(False)
                
                # Reset selection label and button styles
                self.selection_label.setText("No section selected")
                self.mark_start_button.setStyleSheet(self.highlight_color)
                self.mark_end_button.setStyleSheet(self.default_color)
                self.add_section_button.setStyleSheet(self.default_color)
                
                # Load with pydub (for processing)
                self.song = AudioSegment.from_file(file)
                self.song_path = file
                
                # Load with QMediaPlayer (for playback)
                self.player.setSource(QUrl.fromLocalFile(file))
                
                # Show filename
                filename = os.path.basename(self.song_path)
                self.song_label.setText(filename)
                self.song_label.setStyleSheet("""
                    color: #FFFFFF;
                    font-style: normal;
                    padding: 2px;
                """)
                
                # Calculate song length from pydub and set slider range
                self.song_length = len(self.song) / 1000  # Convert to seconds
                # Multiply by 100 to handle 2 decimal places
                self.timeline_slider.setRange(0, int(self.song_length * 100))
                
                # Reset current time and update display with proper decimal places
                self.current_time = 0.0
                self.timeline_slider.setValue(0)
                self.time_display.setText(f"00:00.00 / {format_time_precise(self.song_length)}")
                
                self.update_status("Song loaded successfully!")
                
            except Exception as e:
                self.update_status(f"Error loading song: {str(e)}")
                self.song = None
                self.song_path = None
                self.time_display.setText("00:00.00 / 00:00.00")
                self.song_label.setText("No song loaded")
                self.song_label.setStyleSheet("""
                    color: gray;
                    font-style: italic;
                    padding: 2px;
                """)

    def toggle_play(self):
        if self.song is None:
            self.status_label.setText("Error: No song loaded!")
            return

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPlay))
            self.is_playing = False
        else:
            self.player.play()
            self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPause))
            self.is_playing = True

    def on_position_changed(self, position):
        # Convert position from milliseconds to seconds with 2 decimal places
        self.current_time = position / 1000
        self.timeline_slider.blockSignals(True)
        self.timeline_slider.setValue(int(self.current_time * 100))  # Multiply by 100 for slider
        self.timeline_slider.blockSignals(False)
        self.update_time_display(self.current_time)

    def on_duration_changed(self, duration):
        # Convert duration from milliseconds to seconds
        self.song_length = duration / 1000
        self.timeline_slider.setRange(0, int(self.song_length * 100))

    def on_slider_change(self):
        if not self.song:
            return
        
        # Store playing state when slider drag starts
        if not hasattr(self, 'was_playing_before_seek'):
            self.was_playing_before_seek = self.is_playing
            if self.is_playing:
                self.player.pause()
                self.is_playing = False
        
        # Update position without starting playback
        position = self.timeline_slider.value() / 100.0
        self.player.setPosition(int(position * 1000))
        self.current_time = position
        self.update_time_display(position)

    def on_slider_released(self):
        if not self.song:
            return
        
        # Resume playback if it was playing before
        if hasattr(self, 'was_playing_before_seek') and self.was_playing_before_seek:
            self.player.play()
            self.is_playing = True
            self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPause))
            self.update_timer.start()
        
        # Clean up the temporary state
        if hasattr(self, 'was_playing_before_seek'):
            delattr(self, 'was_playing_before_seek')

    def set_volume(self):
        volume = self.volume_slider.value() / 100.0  # Convert to 0-1 range
        self.audio_output.setVolume(volume)
        self.volume_percentage.setText(f"{int(volume * 100)}%")

    def update_time(self):
        if self.is_playing and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            current_ms = self.player.position()
            if current_ms >= 0:
                self.current_time = current_ms / 1000.0
                # Update slider position with 2 decimal precision
                self.timeline_slider.blockSignals(True)
                self.timeline_slider.setValue(int(self.current_time * 100))
                self.timeline_slider.blockSignals(False)
                self.update_time_display(self.current_time)
                
                # Check if we've reached the end of the song
                if current_ms >= self.player.duration():
                    self.stop_audio()
                    return
        else:
            if self.is_playing:  # If the song has finished
                self.stop_audio()
            else:
                self.update_timer.stop()
                self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPlay))

    def update_time_display(self, current_time):
        if not self.song:
            self.time_display.setText("00:00.00 / 00:00.00")
            return
        
        # Always format both times with format_time_precise
        current_formatted = format_time_precise(float(current_time))
        total_formatted = format_time_precise(float(self.song_length))
        self.time_display.setText(f"{current_formatted} / {total_formatted}")

    def adjust_time(self, delta):
        if not self.song:
            return
            
        # Rate limiting for seeking operations
        current_time = QTime.currentTime().msecsSinceStartOfDay()
        if current_time - self.last_seek_time < self.seek_cooldown:
            return
        self.last_seek_time = current_time
            
        # Calculate new time with 2 decimal precision
        new_time = round(self.current_time + delta, 2)  # Changed from round(..., 1)
        new_time = max(0, min(new_time, self.song_length))
        
        # Store current playing state but don't resume after
        was_playing = self.is_playing
        if was_playing:
            self.is_playing = False
            self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPlay))
            self.update_timer.stop()
            self.player.pause()
        
        # Set the new position directly without using the debounce mechanism
        self.current_time = new_time
        self.timeline_slider.setValue(int(new_time * 100))
        if self.player.duration() > 0:
            # Just set position in milliseconds directly
            self.player.setPosition(int(new_time * 1000))
        self.update_time_display(new_time)

    def setup_shortcuts(self):
        # Space bar for play/pause
        self.play_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.play_shortcut.activated.connect(self.toggle_play)
        
        # Left/Right arrow keys for time adjustment (1 second)
        self.left_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.left_shortcut.activated.connect(lambda: self.adjust_time(-1.0))
        
        self.right_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.right_shortcut.activated.connect(lambda: self.adjust_time(1.0))
        
        # Up/Down arrow keys for volume control
        self.up_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.up_shortcut.activated.connect(lambda: self.adjust_volume(5))  # Increase by 5%
        
        self.down_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.down_shortcut.activated.connect(lambda: self.adjust_volume(-5))  # Decrease by 5%
        
        # Enter key for section marking
        self.enter_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
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
        self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPlay))
        self.update_timer.stop()
        # Reset position to start with proper decimal places
        self.current_time = 0.0
        self.timeline_slider.setValue(0)
        self.update_time_display(0.0)  # Pass as float

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
            start_formatted = format_time_precise(self.current_section_start)
            
            if self.current_section_end is not None:
                end_formatted = format_time_precise(self.current_section_end)
                self.selection_label.setText(f"Selected: {start_formatted} to {end_formatted}")
            else:
                self.selection_label.setText(f"Start: {start_formatted} - Click 'Mark End' to set end point")
        else:
            self.selection_label.setText("No section selected")

    def add_section(self):
        if self.current_section_start is None or self.current_section_end is None:
            self.status_label.setText("Error: Please select both start and end points!")
            return
            
        self.sections.append((self.current_section_start, self.current_section_end))
        
        start_formatted = format_time_precise(self.current_section_start)
        end_formatted = format_time_precise(self.current_section_end)
        
        self.section_list_widget.addItem(
            f"Section {len(self.sections)}: {start_formatted} to {end_formatted}"
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
        if message.lower().startswith("error"):
            self.status_label.setStyleSheet("""
                color: #e74c3c;
                font-size: 14px;
                font-weight: bold;
                padding: 2px;
            """)
        else:
            self.status_label.setStyleSheet("""
                color: #3498db;
                font-size: 14px;
                font-weight: bold;
                padding: 2px;
            """)
        self.status_label.setText(message)

    def closeEvent(self, event):
        # Stop update timer first
        self.update_timer.stop()
        
        # Stop playback and reset state
        if hasattr(self, 'is_playing'):
            self.is_playing = False
        
        # Release QMediaPlayer resources in a safe order
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
        # Release QMediaPlayer resources
        if hasattr(self, 'player') and self.player:
            self.player.stop()  # Just stop, no need to release
            self.player = None
        
        if hasattr(self, 'audio_output') and self.audio_output:
            self.audio_output = None  # No need to release, just remove reference
        
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

    def perform_seek(self):
        if self.pending_seek_position is None:
            return
        
        # Get the final position we want to seek to
        new_time = self.pending_seek_position
        self.current_time = new_time
        
        if self.player.duration() > 0:
            # Convert to milliseconds for QMediaPlayer
            position_ms = int(new_time * 1000)
            self.player.setPosition(position_ms)
            
            # Resume playback if it was playing before
            if self.was_playing:
                QTimer.singleShot(100, self.resume_playback)
            
        self.update_time_display(self.current_time)
        self.pending_seek_position = None

    def resume_playback(self):
        self.player.play()
        self.is_playing = True
        self.was_playing = False
        self.play_button.setIcon(self.create_white_icon(QStyle.StandardPixmap.SP_MediaPause))
        self.update_timer.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = resources.get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    
    apply_dark_mode(app)
    window = AudioApp()
    window.show()
    sys.exit(app.exec())  # Remove underscore from exec_ in PyQt6
