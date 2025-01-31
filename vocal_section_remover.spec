# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
import sys
import os
from PyInstaller.utils.hooks import collect_all
import site
import demucs
from PyInstaller.utils.hooks import collect_submodules
import torch
from demucs.pretrained import get_model
import shutil
import tempfile

# Fix for RecursionError
sys.setrecursionlimit(sys.getrecursionlimit() * 5)

block_cipher = None

# Get FFmpeg path from pydub
from pydub.utils import which
ffmpeg_path = which("ffmpeg")
ffprobe_path = which("ffprobe")

# Get path to demucs models directly from the demucs package
demucs_path = os.path.dirname(demucs.__file__)
models_path = os.path.join(demucs_path, 'models')

# Print paths for debugging
print(f"Demucs path: {demucs_path}")
print(f"Models path: {models_path}")

# Create a temporary directory in the project folder
temp_dir = os.path.join(os.path.abspath(SPECPATH), 'temp_build')
os.makedirs(temp_dir, exist_ok=True)
temp_cache_dir = os.path.join(temp_dir, 'demucs_cache')
os.makedirs(temp_cache_dir, exist_ok=True)
os.environ['TORCH_HOME'] = temp_cache_dir

# Download model and set up paths
print("Pre-downloading Demucs model...")
model = get_model('htdemucs')  # This will download the model to project temp folder

# Get the path to the downloaded model and its directory
temp_model_dir = os.path.join(temp_cache_dir, 'hub', 'checkpoints')
temp_model_file = os.path.join(temp_model_dir, '955717e8-8726e21a.th')

# Define the target path (where we want it in the packaged app)
target_model_path = 'hub/checkpoints'  # This will go inside PyInstaller's _internal

# Verify model exists
if not os.path.exists(temp_model_file):
    raise FileNotFoundError(f"Model file not found at {temp_model_file}")

print(f"Model downloaded to: {temp_model_file}")
print(f"Will be packaged to: {target_model_path}")

# Add to datas with the correct target path - copy the entire checkpoints directory
datas = [
    ('assets', 'assets'),
    ('README.md', '.'),
    (temp_model_dir, target_model_path),  # Copy the entire checkpoints directory
]

# Clean up temp directory at the end
def cleanup_temp():
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
import atexit
atexit.register(cleanup_temp)

# Add all files from demucs directory
for root, dirs, files in os.walk(demucs_path):
    for file in files:
        full_path = os.path.join(root, file)
        rel_path = os.path.relpath(root, os.path.dirname(demucs_path))
        datas.append((full_path, os.path.join('demucs', rel_path)))

binaries = [
    (ffmpeg_path, '.'),  # Include FFmpeg executable
    (ffprobe_path, '.')  # Include FFprobe executable
]

hiddenimports = [
    'pydub', 
    'PyQt6.sip',
    'PyQt6.QtMultimedia',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'soundfile',
    'demucs',
    'demucs.separate',
    'demucs.models.htdemucs',
    'demucs.models.htdemucs_ft',
    'demucs.models.htdemucs_6s',
    'demucs.audio',
    'demucs.utils',
    'numpy',
    'numpy.core',
    'numpy.core.multiarray',
    'numpy.core.numeric',
    'numpy.core.umath',
    'numpy.lib',
    'numpy.linalg',
    'scipy',
    'torch',
    'torchaudio',
    'julius',
    'openunmix',
    'typing_extensions'
]

# Add Demucs related packages but exclude tensorflow
tmp_ret = collect_all('demucs')
datas += tmp_ret[0]
binaries += tmp_ret[1]

# Exclude tensorflow related imports from hiddenimports
hiddenimports = [imp for imp in hiddenimports + tmp_ret[2] 
                 if not imp.startswith('tensorflow')]

# Add all numpy submodules
numpy_hidden_imports = collect_submodules('numpy')
hiddenimports.extend(numpy_hidden_imports)

a = Analysis(
    ['app.py'],
    pathex=[os.path.abspath(SPECPATH)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tensorflow', 'tensorboard', 'keras'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VocalSectionRemover',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True temporarily to see error messages
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app_icon.ico'
)

# Remove README from datas before COLLECT
readme_data = None
for idx, (src, dst, type_) in enumerate(a.datas):
    if src == 'README.md':
        readme_data = a.datas.pop(idx)
        break

# Create a hook to set file permissions after collection
def make_files_writable(analysis):
    for dest, src, type_ in analysis:
        if 'hub/checkpoints' in dest:
            try:
                os.chmod(src, 0o777)
            except:
                pass
    return analysis  # Return the analysis object unchanged

# Register the hook
a.datas = make_files_writable(a.datas)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VocalSectionRemover',
)

# Copy README to root directory
import shutil
if readme_data:
    shutil.copy2(readme_data[0], os.path.join('dist', 'VocalSectionRemover', 'README.md')) 