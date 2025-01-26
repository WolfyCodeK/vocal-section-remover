# Build Command
pyinstaller vocal_section_remover.spec

# Audio Section Editor

A tool for removing vocals from specific sections of audio files.

## Installation

1. Install Demucs:
2. Download and run the Audio Section Editor executable from the releases page.

## Requirements

- Windows 10 or later
- At least 4GB RAM
- Demucs installed on the system

## Usage

1. Click "Load Song" to select an audio file
2. Add sections where you want vocals removed by entering start and end times
3. Click "Process Sections" to remove vocals from the selected sections
4. Find the processed file as "output_with_vocals_removed.mp3" in the same folder

## Known Issues

- First time startup might be slow due to Demucs model loading
- Processing large files requires significant RAM and CPU power
