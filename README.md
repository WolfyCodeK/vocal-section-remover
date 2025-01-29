# Vocal Section Remover

A PyQt6-based application for removing vocals from specific sections of audio files.

## Features

- Load and play audio files (MP3, WAV)
- Mark sections for vocal removal
- Process multiple sections in one go
- Export processed audio with both original and instrumental versions of marked sections

## Installation

1. Clone the repository:
bash
git clone https://github.com/yourusername/vocal-section-remover.git
cd vocal-section-remover
2. Create a virtual environment (recommended):
bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
3. Install dependencies:
bash
pip install -e

## Usage

1. Run the application:
bash
vocal-section-remover

2. Click "Import File" to load an audio file
3. Use the timeline to navigate through the audio
4. Mark sections where you want vocals removed:
   - Click "Mark Start" or press Enter
   - Navigate to end point
   - Click "Mark End" or press Enter again
   - Click "Add Section" or press Enter to confirm
5. Repeat for additional sections
6. Click "Process Sections" to remove vocals from marked sections

## Keyboard Shortcuts

- Space: Play/Pause
- Left/Right Arrow: Seek backward/forward
- Up/Down Arrow: Adjust volume
- Enter: Mark section start/end/add