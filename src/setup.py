from setuptools import setup, find_packages

setup(
    name="vocal-section-remover",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'PyQt6>=6.5.2',
        'pydub>=0.25.1',
        'demucs>=4.0.1',
        'soundfile',
    ],
    entry_points={
        'console_scripts': [
            'vocal-section-remover=src.main:main',
        ],
    },
    package_data={
        'src': ['assets/*'],
    },
    python_requires='>=3.9',
) 