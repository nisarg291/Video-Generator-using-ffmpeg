Video Slideshow Generator
=========================

This Python script creates a video slideshow from images and background music, with text overlays and captions.

Features
--------
- Combines multiple images into a video with a fixed size (1920x1080).
- Adds background music from MP3 files.
- Overlays white text at the top-left (optional) and a black caption at the bottom-center with a semi-transparent background.
- Applies image transformations (grayscale, rotate, or resize).
- Stores temporary files in a `temp` folder.

Requirements
------------
- Python 3.x
- PIL (Pillow): Run `pip install Pillow` to install.
- FFmpeg: Download from https://github.com/BtbN/FFmpeg-Builds/releases and update `FFMPEG_PATH` in the script to point to `ffmpeg.exe`.

Usage
-----
Run the script from the command line:

    python script.py -i image1.jpg image2.jpg -m music.mp3 -t "Overlay Text" -c "Demo Caption" -tr grayscale -d 20 -o final_video.mp4

Arguments
---------
- `-i/--images`: List of image files (required).
- `-m/--musics`: List of music files (required).
- `-t/--text`: White text at top-left (optional).
- `-c/--caption`: Black caption at bottom-center (required).
- `-tr/--transformation`: Image effect (`grayscale`, `rotate`, `resize`) (required).
- `-d/--duration`: Total video length in seconds (default: 10).
- `-o/--output`: Output video file (default: `final_video.mp4`).

Output
------
- Final video saved as specified (e.g., `final_video.mp4`).
- Temporary files (images, audio, segments) stored in `temp` folder.

Notes
-----
- Ensure FFmpeg is installed and `FFMPEG_PATH` points to `ffmpeg.exe`.
- Images are resized to 1920x1080; adjust `TARGET_WIDTH` and `TARGET_HEIGHT` in the script if needed.
- Uncomment the cleanup line in `main()` to delete the `temp` folder after running.
