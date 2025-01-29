# Vocal Section Remover - Project Documentation

## Project Structure

```
vocal_section_remover/
├── src/
│   ├── audio/                    # Audio processing components
│   │   ├── file_loader.py        # Handles audio file loading
│   │   ├── player.py             # Audio playback functionality
│   │   └── processor.py          # Vocal removal processing
│   ├── gui/                      # GUI components
│   │   ├── widgets/              # Individual UI widgets
│   │   │   ├── timeline.py
│   │   │   ├── volume_control.py
│   │   │   ├── section_controls.py
│   │   │   └── status_bar.py
│   │   ├── styles/              # UI styling
│   │   │   └── dark_theme.py
│   │   └── main_window.py       # Main application window
│   ├── utils/                   # Utility functions and constants
│   │   ├── constants.py         # Application-wide constants
│   │   ├── time_format.py       # Time formatting utilities
│   │   └── resources.py         # Resource management
│   └── main.py                  # Application entry point
├── assets/                      # Application assets
│   └── app_icon.ico
└── setup.py                     # Installation configuration
```

## Component Overview

### Audio Components

1. **FileLoader** (`audio/file_loader.py`)
   - Runs in a separate thread to load audio files
   - Uses `pydub` to handle various audio formats
   - Emits signals for load completion and status updates

2. **AudioPlayer** (`audio/player.py`)
   - Manages audio playback using PyQt6's QMediaPlayer
   - Handles play/pause, seeking, and volume control
   - Provides position updates and playback state changes

3. **AudioProcessor** (`audio/processor.py`)
   - Handles vocal removal using the Demucs model
   - Processes marked sections in a separate thread
   - Creates output files with original and processed sections

### GUI Components

1. **MainWindow** (`gui/main_window.py`)
   - Main application window
   - Coordinates all components and user interactions
   - Manages application state and file operations

2. **Timeline** (`gui/widgets/timeline.py`)
   - Displays playback position and duration
   - Provides playback controls and seeking
   - Shows current audio file progress

3. **VolumeControl** (`gui/widgets/volume_control.py`)
   - Handles volume adjustment
   - Displays current volume level
   - Provides visual feedback

4. **SectionControls** (`gui/widgets/section_controls.py`)
   - Manages section marking and listing
   - Handles adding/removing sections
   - Controls section processing

5. **StatusBar** (`gui/widgets/status_bar.py`)
   - Displays application status messages
   - Shows error notifications
   - Provides user feedback

### Utility Components

1. **Constants** (`utils/constants.py`)
   - Defines application-wide constants
   - Window dimensions
   - Color schemes
   - Keyboard shortcuts

2. **TimeFormat** (`utils/time_format.py`)
   - Provides time formatting functions
   - Converts between different time formats
   - Ensures consistent time display

3. **Resources** (`utils/resources.py`)
   - Manages application resources
   - Handles asset paths
   - Ensures resource availability

## Data Flow

1. **Audio File Loading**
   ```
   User → MainWindow → FileLoader → AudioPlayer
                    ↓
                 Updates UI
   ```

2. **Section Marking**
   ```
   User → Timeline → SectionControls → MainWindow
                                   ↓
                            Updates Section List
   ```

3. **Processing Flow**
   ```
   User → SectionControls → AudioProcessor → Output Files
                         ↓
                  Status Updates → StatusBar
   ```

## Signal Connections

1. **Audio Player Signals**
   - `position_changed`: Updates timeline position
   - `playback_state_changed`: Updates play/pause button state

2. **Section Control Signals**
   - `section_added`: Notifies when new section is added
   - `section_deleted`: Handles section removal
   - `process_requested`: Initiates vocal removal

3. **File Loader Signals**
   - `finished`: Handles completed file loading
   - `status_update`: Updates status bar

## Key Features

1. **Audio Playback**
   - Real-time position updates
   - Precise seeking
   - Volume control
   - Keyboard shortcuts

2. **Section Management**
   - Mark start/end points
   - Visual section list
   - Section deletion
   - Validation checks

3. **Processing**
   - Multi-threaded processing
   - Progress updates
   - Error handling
   - Output file organization

## Development Guidelines

1. **Adding New Features**
   - Create appropriate widget class if UI-related
   - Use signals for component communication
   - Follow existing naming conventions
   - Update documentation

2. **Error Handling**
   - Use status bar for user feedback
   - Implement appropriate error checks
   - Maintain application stability

3. **Code Style**
   - Follow PEP 8 guidelines
   - Document classes and methods
   - Use type hints where appropriate
   - Keep methods focused and concise

## Common Operations

1. **Loading Files**
   ```python
   self.file_loader = FileLoader(file_path)
   self.file_loader.finished.connect(self._on_file_loaded)
   self.file_loader.start()
   ```

2. **Processing Sections**
   ```python
   self.audio_processor = AudioProcessor(song, sections, song_path)
   self.audio_processor.status_update.connect(self.status_bar.set_status)
   self.audio_processor.start()
   ```

3. **Adding UI Components**
   ```python
   def setup_ui(self):
       layout = QVBoxLayout(self)
       # Add widgets
       layout.addWidget(widget)
       # Connect signals
       widget.signal.connect(self.handler)
   ```