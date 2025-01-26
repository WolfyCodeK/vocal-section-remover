# Audio Section Editor

A desktop application for editing audio files by marking sections and removing vocals from those sections. The app allows you to load an audio file, mark specific sections, and process those sections to remove vocals while keeping the rest of the song intact.

## Features

- Load and play MP3/WAV audio files
- Mark specific sections of the audio for vocal removal
- Preview sections before processing
- Process multiple sections in one go
- Keyboard shortcuts for quick control
- Dark mode interface
- Volume control
- Precise timeline navigation

## Usage

1. Click "Import File" to load an audio file (MP3 or WAV)
2. Use the playback controls to navigate the audio:
   - Play/Pause button
   - Timeline slider
   - 1-second forward/backward buttons
   - Volume slider

3. Mark sections for vocal removal:
   - Click "Mark Start" or press Enter at the desired start point
   - Click "Mark End" or press Enter again at the desired end point
   - Click "Add Section" or press Enter a third time to add the section
   - Use "Cancel" to abort the current section marking

4. Manage sections:
   - View all marked sections in the list
   - Select and delete unwanted sections
   - Add multiple sections as needed

5. Click "Process Sections" to remove vocals from all marked sections
   - The app will create a new file with vocals removed from marked sections
   - Output will be saved in a timestamped folder with the original filename

## Keyboard Shortcuts

- **Space**: Play/Pause
- **Left Arrow**: Move back 1 second
- **Right Arrow**: Move forward 1 second
- **Up Arrow**: Increase volume by 5%
- **Down Arrow**: Decrease volume by 5%
- **Enter**: Mark section (Start → End → Add)

## Output

The processed file will be saved in an output folder named after the original file with a timestamp:
- `output/songname_YYYYMMDD_HHMMSS/output.mp3`
- A text file with section information is included in the output folder

## Requirements

- Windows operating system
- VLC media player installed
- Python dependencies (if running from source)

## Notes

- The original audio file is never modified
- A temporary working copy is created during processing
- The app automatically cleans up temporary files

## Installation

1. Install Demucs:
2. Download and run the Audio Section Editor executable from the releases page.

## Known Issues

- First time startup might be slow due to Demucs model loading
- Processing large files requires significant RAM and CPU power
