# Voice Section Remover

A desktop application that lets you remove vocals from specific sections of songs while keeping the instrumental background. Perfect for creating custom karaoke versions or removing unwanted vocal parts from songs.

## What It Does

- Load MP3 or WAV audio files
- Play and navigate through songs
- Mark sections where you want vocals removed
- Process multiple sections at once
- Keep the original file untouched - creates a new edited version

## How to Use

1. **Open a Song**
   - Click "Import File" to load your audio file
   - The song name will appear and the timeline will update

2. **Navigate the Song**
   - Click Play/Pause or press Space to start/stop playback
   - Use the timeline slider to jump to any part
   - Use the 1-second buttons or arrow keys for precise navigation
   - Adjust volume with the slider or Up/Down arrows

3. **Mark Sections**
   - Navigate to where you want to start removing vocals
   - Click "Mark Start" or press Enter
   - Navigate to where you want to stop removing vocals
   - Click "Mark End" or press Enter
   - Click "Add Section" or press Enter to confirm
   - Repeat for multiple sections if needed
   - Use "Cancel" if you make a mistake

4. **Process the Song**
   - Click "Process Sections" when you're ready
   - Wait for processing to complete
   - Find your edited song in the "output" folder
   - Each processed file is in its own timestamped folder

## Keyboard Controls

- **Space**: Play/Pause
- **Left Arrow**: Go back 1 second
- **Right Arrow**: Go forward 1 second
- **Up Arrow**: Volume up
- **Down Arrow**: Volume down
- **Enter**: Mark sections (Start → End → Add)

## Finding Your Processed Files

After processing, your new audio file will be in:
- A folder named `output`
- In a subfolder with your song's name and the current date/time
- Along with a text file listing the sections that were processed

## Important Notes

- Your original audio file is never changed
- Processing might take a few minutes depending on file size
- First startup may be slower while the app loads
- Keep the app open until processing is complete