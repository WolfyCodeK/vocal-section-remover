import os
import pygame
import sys
from pydub import AudioSegment
import subprocess
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QFileDialog, QListWidget, QSlider, QHBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

# Initialize Pygame mixer
pygame.mixer.init()

# Ensure the output directory exists
os.makedirs('output/temp_section', exist_ok=True)

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
            # Run Demucs to separate vocals
            subprocess.run(["demucs", "-n", "htdemucs", "--two-stems=vocals", "temp_section.wav"])

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
        self.initUI()
        self.song = None
        self.song_path = None
        self.sections = []
        self.is_playing = False
        self.current_time = 0
        self.audio_processor = None  # To keep track of the audio processor thread

    def initUI(self):
        self.setWindowTitle("Audio Section Editor")

        # Layout
        layout = QVBoxLayout()

        # Load song button
        self.load_button = QPushButton("Load Song", self)
        self.load_button.clicked.connect(self.load_song)
        layout.addWidget(self.load_button)

        # Display the loaded song path
        self.song_label = QLabel("No song loaded", self)
        layout.addWidget(self.song_label)

        # Play/Pause button
        self.play_button = QPushButton("Play", self)
        self.play_button.clicked.connect(self.toggle_play)
        layout.addWidget(self.play_button)

        # Stop button
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop_audio)
        layout.addWidget(self.stop_button)

        # Timeline and Volume Control Layout
        timeline_layout = QHBoxLayout()

        # Timeline slider (much longer)
        self.timeline_slider = QSlider(Qt.Horizontal, self)
        self.timeline_slider.setRange(0, 100)
        self.timeline_slider.valueChanged.connect(self.on_slider_change)
        timeline_layout.addWidget(self.timeline_slider)

        # Volume slider (vertical)
        self.volume_slider = QSlider(Qt.Vertical, self)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)  # Default volume is 100%
        self.volume_slider.valueChanged.connect(self.set_volume)
        timeline_layout.addWidget(self.volume_slider)

        # Volume percentage label
        self.volume_percentage = QLabel("100%", self)
        timeline_layout.addWidget(self.volume_percentage)

        layout.addLayout(timeline_layout)

        # Time display label
        self.time_display = QLabel("0:00 / 0:00", self)
        layout.addWidget(self.time_display)

        # Start and End time input fields
        self.start_time_input = QLineEdit(self)
        self.start_time_input.setPlaceholderText("Enter start time in seconds")
        layout.addWidget(self.start_time_input)

        self.end_time_input = QLineEdit(self)
        self.end_time_input.setPlaceholderText("Enter end time in seconds")
        layout.addWidget(self.end_time_input)

        # Add Section button
        self.add_section_button = QPushButton("Add Section", self)
        self.add_section_button.clicked.connect(self.add_section)
        layout.addWidget(self.add_section_button)

        # List to display sections added
        self.section_list_widget = QListWidget(self)
        layout.addWidget(self.section_list_widget)

        # Delete Section button
        self.delete_section_button = QPushButton("Delete Selected Section", self)
        self.delete_section_button.clicked.connect(self.delete_section)
        layout.addWidget(self.delete_section_button)

        # Process button
        self.process_button = QPushButton("Process Sections", self)
        self.process_button.clicked.connect(self.process_sections)
        layout.addWidget(self.process_button)

        # Status label
        self.status_label = QLabel("Status: Waiting for song...", self)
        layout.addWidget(self.status_label)

        # Set main widget and layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setGeometry(300, 300, 400, 500)

    def load_song(self):
        file, _ = QFileDialog.getOpenFileName(self, "Load Song", "", "Audio Files (*.mp3 *.wav)")
        if file:
            self.song_path = file
            self.song = AudioSegment.from_file(file)
            self.song_label.setText(f"Loaded: {os.path.basename(self.song_path)}")
            self.status_label.setText("Song loaded successfully!")

            # Load the audio file using pygame
            pygame.mixer.music.load(file)
            self.song_length = pygame.mixer.Sound(file).get_length()
            self.timeline_slider.setRange(0, int(self.song_length))
            self.current_time = 0

    def toggle_play(self):
        if self.song is None:
            self.status_label.setText("Error: No song loaded!")
            return

        if self.is_playing:
            pygame.mixer.music.pause()
            self.play_button.setText("Play")
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
            self.current_time = pygame.mixer.music.get_pos() / 1000.0
            self.timeline_slider.setValue(int(self.current_time))
            
            # Update the time display
            minutes, seconds = divmod(int(self.current_time), 60)
            total_minutes, total_seconds = divmod(int(self.song_length), 60)
            self.time_display.setText(f"{minutes:02}:{seconds:02} / {total_minutes:02}:{total_seconds:02}")
            
            # Continue updating the time every 100ms
            QTimer.singleShot(100, self.update_time)

    def on_slider_change(self):
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
        self.volume_percentage.setText(f"{self.volume_slider.value()}%")

    def get_section_times(self):
        try:
            start_time = int(self.start_time_input.text())
            end_time = int(self.end_time_input.text())
            if end_time <= start_time:
                self.status_label.setText("Error: End time must be after start time!")
                return None, None
            return start_time, end_time
        except ValueError:
            self.status_label.setText("Error: Please enter valid integers for start and end times!")
            return None, None

    def add_section(self):
        start_time, end_time = self.get_section_times()
        if start_time is None or end_time is None:
            return
        self.sections.append((start_time, end_time))
        self.section_list_widget.addItem(f"Section {len(self.sections)}: {start_time}s to {end_time}s")
        self.status_label.setText(f"Section {len(self.sections)} added: {start_time}s to {end_time}s")

    def delete_section(self):
        selected_item = self.section_list_widget.currentItem()
        if selected_item:
            section_text = selected_item.text()
            section_idx = int(section_text.split(":")[0].split()[1]) - 1
            
            # Remove the section from the list
            self.sections.pop(section_idx)
            
            # Update the section list display
            self.section_list_widget.takeItem(self.section_list_widget.row(selected_item))
            
            # Re-number the sections in the list widget
            for i in range(self.section_list_widget.count()):
                item = self.section_list_widget.item(i)
                item.setText(f"Section {i + 1}: {self.sections[i][0]}s to {self.sections[i][1]}s")
            
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
    window = AudioApp()
    window.show()
    sys.exit(app.exec_())
