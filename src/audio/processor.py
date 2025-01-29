import os
import sys
import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from pydub import AudioSegment
from demucs.pretrained import get_model
from demucs.apply import apply_model
from demucs.audio import AudioFile
import torchaudio
from utils.time_format import format_time, format_time_precise

class AudioProcessor(QThread):
    status_update = pyqtSignal(str)

    def __init__(self, song, sections, song_path):
        super().__init__()
        self.song = song
        self.sections = sections
        self.song_path = song_path

    def _setup_output_directory(self):
        """Create output directory with timestamp"""
        base_filename = os.path.splitext(os.path.basename(self.song_path))[0]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join("output", f"{base_filename}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _create_info_file(self, output_dir):
        """Create info text file with section details"""
        info_path = os.path.join(output_dir, "section_info.txt")
        with open(info_path, "w") as f:
            f.write("Vocal Removal Sections:\n\n")
            for idx, (start_time, end_time) in enumerate(self.sections, 1):
                f.write(f"Section {idx}: {format_time(start_time)} to {format_time(end_time)}\n")
            f.write(f"\nOriginal file: {os.path.basename(self.song_path)}\n")
            f.write(f"Processed on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    def _load_model(self):
        """Load the Demucs model"""
        self.status_update.emit("Loading Demucs model...")
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
            model_path = os.path.join(base_path, '_internal')
            os.environ['TORCH_HOME'] = model_path
            os.environ['DEMUCS_OFFLINE'] = '1'
            
            expected_model_path = os.path.join(model_path, 'hub', 'checkpoints', '955717e8-8726e21a.th')
            if not os.path.exists(expected_model_path):
                raise FileNotFoundError(f"Model file not found at: {expected_model_path}")
        
        return get_model('htdemucs')

    def _process_section(self, section, temp_dir, model, idx):
        """Process a single section of audio"""
        start_formatted = format_time_precise(section[0])
        end_formatted = format_time_precise(section[1])
        self.status_update.emit(f"Section {idx} processing from {start_formatted} to {end_formatted}...")
        
        # Extract section audio
        section_audio = self.song[section[0] * 1000:section[1] * 1000]
        
        # Setup temporary files
        temp_section_path = os.path.join(temp_dir, "temp_section.wav")
        temp_novocals_path = os.path.join(temp_dir, "temp_section_no_vocals.wav")
        
        # Export section to temp file
        section_audio.export(
            temp_section_path,
            format="wav",
            parameters=["-analyzeduration", "0", "-probesize", "32", "-loglevel", "error"]
        )

        # Process with Demucs
        audio_file = AudioFile(temp_section_path)
        wav = audio_file.read(streams=0, samplerate=model.samplerate, channels=model.audio_channels)
        ref = wav.mean(0)
        wav = (wav - ref.mean()) / ref.std()
        
        sources = apply_model(model, wav[None], device='cpu', progress=False, num_workers=1)[0]
        sources = sources * ref.std() + ref.mean()
        
        # Mix stems except vocals
        instrumental = sum(sources[i] for i in range(3))  # drums, bass, other
        
        # Save processed audio
        torchaudio.save(temp_novocals_path, instrumental.cpu(), sample_rate=int(model.samplerate))
        
        return AudioSegment.from_file(temp_novocals_path)

    def run(self):
        try:
            output_dir = self._setup_output_directory()
            self._create_info_file(output_dir)
            
            model = self._load_model()
            model.eval()
            
            # Sort sections by start time
            self.sections.sort(key=lambda x: x[0])
            
            # Process sections
            combined = AudioSegment.empty()
            last_end_time = 0
            
            # Create temp directory
            temp_dir = os.path.join("_internal", "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                for idx, (start_time, end_time) in enumerate(self.sections, 1):
                    # Add original audio before section
                    if start_time > last_end_time:
                        combined += self.song[last_end_time * 1000:start_time * 1000]
                    
                    # Add original section
                    section_audio = self.song[start_time * 1000:end_time * 1000]
                    combined += section_audio
                    
                    # Process and add instrumental section
                    instrumental = self._process_section((start_time, end_time), temp_dir, model, idx)
                    combined += instrumental
                    
                    last_end_time = end_time
                
                # Add remaining audio after last section
                if last_end_time < len(self.song) / 1000:
                    combined += self.song[last_end_time * 1000:]
                
                # Export final result
                self.status_update.emit("Exporting final result...")
                output_path = os.path.join(output_dir, "output.mp3")
                combined.export(output_path, format="mp3")
                
                self.status_update.emit(f"Processing complete! Output saved in: {output_dir}")
                
            finally:
                # Cleanup temp files
                self.status_update.emit("Cleaning up temporary files...")
                if os.path.exists(temp_dir):
                    for file in os.listdir(temp_dir):
                        try:
                            os.remove(os.path.join(temp_dir, file))
                        except:
                            pass
                    try:
                        os.rmdir(temp_dir)
                    except:
                        pass
                        
        except Exception as e:
            self.status_update.emit(f"Error during processing: {str(e)}") 