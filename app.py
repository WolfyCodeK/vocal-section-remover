import os
from pydub import AudioSegment
import subprocess
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QFileDialog
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Ensure the output directory exists
os.makedirs('output/temp_section', exist_ok=True)

class AudioProcessor(QThread):
    status_update = pyqtSignal(str)

    def __init__(self, song, start_time, end_time):
        super().__init__()
        self.song = song
        self.start_time = start_time
        self.end_time = end_time

    def run(self):
        self.status_update.emit("Extracting selected section...")
        # Slice the song to the selected section
        section = self.song[self.start_time * 1000:self.end_time * 1000]  # times in milliseconds
        section.export("temp_section.wav", format="wav")  # Export as WAV for better separation

        self.status_update.emit("Running Spleeter to separate vocals and instrumental...")
        # Run Spleeter to separate vocals (using the 4stems model for better separation)
        subprocess.run(["spleeter", "separate", "-p", "spleeter:4stems", "-o", "output", "temp_section.wav"])

        self.status_update.emit("Loading instrumental version...")
        # Ensure the directory exists and the file is created
        other_path = os.path.join('output', 'temp_section', 'other.wav')
        if not os.path.exists(other_path):
            self.status_update.emit(f"Error: Instrumental file not found: {other_path}")
            return

        # Load instrumental version (other.wav contains the instrumental track)
        instrumental = AudioSegment.from_file(other_path)

        self.status_update.emit("Adding song before the selected section...")
        part_before_section = self.song[:self.start_time * 1000]

        self.status_update.emit("Adding song after the selected section...")
        part_after_section = self.song[self.end_time * 1000:]

        # Section with vocals (original section)
        section_with_vocals = section

        # Section without vocals (instrumental version)
        section_without_vocals = instrumental

        self.status_update.emit("Combining sections with and without vocals...")
        # Combine the parts: first the part before the section, then the section with vocals,
        # followed by the same section without vocals, and finally the part after the section
        combined = part_before_section + section_with_vocals + section_without_vocals + part_after_section

        self.status_update.emit("Exporting final result...")
        # Export the final result
        combined.export("output_with_vocals_removed.mp3", format="mp3")

        self.status_update.emit("Cleaning up temporary files...")
        # Clean up temporary files
        os.remove("temp_section.wav")
        os.remove(other_path)
        shutil.rmtree("output/temp_section", ignore_errors=True)
        os.rmdir("output")  # Remove the output directory if it's empty
        self.status_update.emit("Processing complete! Saved as output_with_vocals_removed.mp3")

class AudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.song = None
        self.song_path = None

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

        # Start and End time input fields
        self.start_time_input = QLineEdit(self)
        self.start_time_input.setPlaceholderText("Enter start time in seconds")
        layout.addWidget(self.start_time_input)

        self.end_time_input = QLineEdit(self)
        self.end_time_input.setPlaceholderText("Enter end time in seconds")
        layout.addWidget(self.end_time_input)

        # Process button
        self.process_button = QPushButton("Process Section", self)
        self.process_button.clicked.connect(self.process_section)
        layout.addWidget(self.process_button)

        # Status label
        self.status_label = QLabel("Status: Waiting for song...", self)
        layout.addWidget(self.status_label)

        # Set main widget and layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setGeometry(300, 300, 400, 300)

    def load_song(self):
        options = QFileDialog.Options()
        file, _ = QFileDialog.getOpenFileName(self, "Load Song", "", "Audio Files (*.mp3 *.wav)", options=options)
        if file:
            self.song_path = file
            self.song = AudioSegment.from_file(file)
            self.song_label.setText(f"Loaded: {os.path.basename(self.song_path)}")
            self.status_label.setText("Song loaded successfully!")

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

    def process_section(self):
        if not self.song:
            self.status_label.setText("Error: No song loaded!")
            return
        else:
            self.status_label.setText("Processing...")

        start_time, end_time = self.get_section_times()
        if start_time is None or end_time is None:
            return

        # Start the background thread for processing the song
        self.processor = AudioProcessor(self.song, start_time, end_time)
        self.processor.status_update.connect(self.update_status)
        self.processor.start()

    def update_status(self, message):
        self.status_label.setText(message)

def main():
    app = QApplication([])
    window = AudioApp()
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()
