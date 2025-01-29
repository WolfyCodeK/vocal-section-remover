from PyQt6.QtCore import QThread, pyqtSignal
from pydub import AudioSegment

class FileLoader(QThread):
    finished = pyqtSignal(tuple)
    status_update = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.status_update.emit("Loading audio file...")
            song = AudioSegment.from_file(self.file_path)
            self.finished.emit((song, self.file_path))
        except Exception as e:
            self.status_update.emit(f"Error loading file: {str(e)}")
            self.finished.emit((None, None)) 