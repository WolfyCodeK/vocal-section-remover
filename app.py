import os
from pydub import AudioSegment
import subprocess
import shutil
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QFileDialog, QListWidget
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Ensure the output directory exists
os.makedirs('output/temp_section', exist_ok=True)

class AudioProcessor(QThread):
    status_update = pyqtSignal(str)

    def __init__(self, song, sections):
        super().__init__()
        self.song = song
        self.sections = sections

    def run(self):
        combined = AudioSegment.empty()  # Start with an empty audio segment
        last_end_time = 0  # Keep track of the last section's end time

        for idx, (start_time, end_time) in enumerate(self.sections, start=1):
            self.status_update.emit(f"Section {idx} processing from {start_time}s to {end_time}s...")
            # Slice the song to the selected section
            section = self.song[start_time * 1000:end_time * 1000]  # times in milliseconds
            section.export("temp_section.wav", format="wav")  # Export as WAV for better separation

            self.status_update.emit(f"Running Spleeter for section {idx}...")
            # Run Spleeter to separate vocals (using the 4stems model for better separation)
            subprocess.run(["spleeter", "separate", "-p", "spleeter:4stems", "-o", "output", "temp_section.wav"])

            self.status_update.emit(f"Loading instrumental version for section {idx}...")
            # Ensure the directory exists and the file is created
            other_path = os.path.join('output', 'temp_section', 'other.wav')
            if not os.path.exists(other_path):
                self.status_update.emit(f"Error: Instrumental file not found for section {idx}")
                return

            # Load instrumental version (other.wav contains the instrumental track)
            instrumental = AudioSegment.from_file(other_path)

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
        shutil.rmtree("output/temp_section", ignore_errors=True)
        os.rmdir("output")  # Remove the output directory if it's empty
        self.status_update.emit("Processing complete! Saved as output_with_vocals_removed.mp3")

class AudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.song = None
        self.song_path = None
        self.sections = []

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

        self.setGeometry(300, 300, 400, 400)

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

    def add_section(self):
        start_time, end_time = self.get_section_times()
        if start_time is None or end_time is None:
            return
        self.sections.append((start_time, end_time))
        self.section_list_widget.addItem(f"Section {len(self.sections)}: {start_time}s to {end_time}s")
        self.status_label.setText(f"Section {len(self.sections)} added: {start_time}s to {end_time}s")

    def delete_section(self):
        selected_item = self.section_list_widget.currentRow()
        if selected_item != -1:
            self.sections.pop(selected_item)
            self.section_list_widget.takeItem(selected_item)
            self.status_label.setText("Selected section deleted.")
        else:
            self.status_label.setText("Error: No section selected to delete.")

    def process_sections(self):
        if not self.song:
            self.status_label.setText("Error: No song loaded!")
            return
        if not self.sections:
            self.status_label.setText("Error: No sections added!")
            return

        self.status_label.setText("Processing...")

        # Start the background thread for processing the song
        self.processor = AudioProcessor(self.song, self.sections)
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
