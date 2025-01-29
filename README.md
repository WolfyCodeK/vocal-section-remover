# Vocal Section Remover

A simple tool to remove vocals from specific sections of your music files.

## Quick Start Guide

1. Download and run the `VocalSectionRemover.exe` application
2. Click "Import File" to open your music file (supports MP3 and WAV formats)
3. Use the timeline to find sections where you want to remove vocals
4. Mark and process sections (see detailed instructions below)

## How to Remove Vocals from a Section

1. **Mark the Section**:
   - Play your audio and find where you want vocals removed
   - Click "Mark Start" when you reach the beginning of the section
   - Let the audio play to where you want the section to end
   - Click "Mark End" to complete the section
   - Click "Add Section" to confirm

2. **Process the Audio**:
   - Mark as many sections as you need
   - Click "Process Sections" when you're ready
   - Wait for processing to complete
   - Find your processed file in the `output` folder

## Keyboard Shortcuts

- **Space**: Play/Pause
- **Left Arrow**: Skip back 1 second
- **Right Arrow**: Skip forward 1 second
- **Up Arrow**: Volume up
- **Down Arrow**: Volume down
- **Enter**: Quick section marking
  - First press: Mark start
  - Second press: Mark end
  - Third press: Add section

## Timeline Controls

- Click anywhere on the timeline to jump to that position
- Use the slider to adjust volume
- Watch the time display to see your current position

## Tips & Tricks

- You can mark multiple sections before processing
- Sections can't overlap - finish marking one before starting another
- Processing time depends on the length of your sections
- The original file is never modified - a new file is created

## Output Files

- Find your processed files in the `output` folder
- Each processed file will be in its own timestamped folder
- The output folder contains:
  - `output.mp3`: Your processed audio file
  - `section_info.txt`: Details about the processed sections

## Troubleshooting

**Audio won't play?**
- Make sure your audio file isn't corrupted
- Try a different audio file to test

**Processing taking too long?**
- Processing time depends on section length
- The first processing might take longer while models load

**Can't find your output?**
- Look in the `output` folder where the application is located
- Each processed file gets its own timestamped folder

## Need Help?

If you're having issues:
1. Check the status bar at the bottom of the application for error messages
2. Make sure your audio file is in MP3 or WAV format
3. Ensure you have enough disk space for the output files

## System Requirements

- Windows 10 or later
- At least 4GB RAM recommended
- 2GB free disk space for the application and temporary files

## Important Notes

- Keep the application window open during processing
- Don't modify files in the `output` folder while processing
- The application needs write permissions in its folder