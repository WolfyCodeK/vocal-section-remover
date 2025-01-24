import os
from pydub import AudioSegment
import subprocess
import shutil

# Ensure the output directory exists
os.makedirs('output/temp_section', exist_ok=True)

def load_song():
    song_path = input("Enter the path to the song (mp3 or wav): ")
    if not os.path.exists(song_path):
        print("Error: Song not found!")
        return None
    return AudioSegment.from_file(song_path)

def get_section_times():
    start_time = int(input("Enter the start time in seconds: "))
    end_time = int(input("Enter the end time in seconds: "))
    if end_time <= start_time:
        print("Error: End time must be after start time!")
        return None, None
    return start_time, end_time

def process_section(song, start_time, end_time):
    # Slice the song to the selected section
    section = song[start_time * 1000:end_time * 1000]  # times in milliseconds
    
    # Save section to temporary file
    section.export("temp_section.mp3", format="mp3")
    
    # Run Spleeter to separate vocals
    print("Processing...")
    subprocess.run(["spleeter", "separate", "-p", "spleeter:2stems", "-o", "output", "temp_section.mp3"])
    
    # Ensure the directory exists and the file is created
    instrumental_path = os.path.join('output', 'temp_section', 'accompaniment.wav')
    if not os.path.exists(instrumental_path):
        print(f"Error: Instrumental file not found: {instrumental_path}")
        return
    
    # Load instrumental version
    instrumental = AudioSegment.from_file(instrumental_path)
    
    # First part: the song before the section
    part_before_section = song[:start_time * 1000]
    
    # Second part: the song after the section
    part_after_section = song[end_time * 1000:]
    
    # Section with vocals (original section)
    section_with_vocals = section
    
    # Section without vocals (instrumental version)
    section_without_vocals = instrumental
    
    # Combine the parts: first the part before the section, then the section with vocals,
    # followed by the same section without vocals, and finally the part after the section
    combined = part_before_section + section_with_vocals + section_without_vocals + part_after_section
    
    # Export the final result
    combined.export("output_with_vocals_removed.mp3", format="mp3")
    print("Processing complete! Saved as output_with_vocals_removed.mp3")
    
    # Clean up temporary files
    os.remove("temp_section.mp3")
    os.remove(instrumental_path)
    
    # Use shutil.rmtree to remove the directory and its contents
    shutil.rmtree("output/temp_section", ignore_errors=True)
    os.rmdir("output")  # Remove the output directory if it's empty

def main():
    song = load_song()
    if song:
        start_time, end_time = get_section_times()
        if start_time is not None and end_time is not None:
            process_section(song, start_time, end_time)

if __name__ == "__main__":
    main()
