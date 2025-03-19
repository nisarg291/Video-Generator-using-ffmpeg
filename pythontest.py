from PIL import Image, ImageDraw, ImageFont
import argparse
import subprocess
import os
import shutil

# Path to FFmpeg executable (update if needed)
FFMPEG_PATH = r"C:\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"

# Target video resolution
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080

# Temporary directory name
TEMP_DIR = "temp"

# Check if FFmpeg is available
def check_ffmpeg():
    if not os.path.exists(FFMPEG_PATH) and not shutil.which(FFMPEG_PATH):
        raise RuntimeError(
            f"FFmpeg not found at '{FFMPEG_PATH}'. Download from https://github.com/BtbN/FFmpeg-Builds/releases "
            "and set FFMPEG_PATH to the full path of ffmpeg.exe."
        )

# Resolve file paths
def resolve_path(path, script_dir):
    abs_path = os.path.abspath(os.path.join(script_dir, path) if not os.path.isabs(path) else path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File '{abs_path}' not found.")
    return abs_path

# Ensure temp directory exists
def ensure_temp_dir(script_dir):
    temp_path = os.path.join(script_dir, TEMP_DIR)
    if not os.path.exists(temp_path):
        os.makedirs(temp_path)
    return temp_path

# Process image with fixed resizing, transformation, text overlay, and caption
def process_image(image_path, text, caption, transformation, index, temp_dir):
    try:
        print(f"Processing image: {image_path}")
        img = Image.open(image_path)
        
        # Resize to fixed target size (1920x1080) before transformation
        img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)

        # Apply transformation on the fixed-size image
        if transformation == "grayscale":
            img = img.convert("L")
        elif transformation == "rotate":
            img = img.rotate(90)
        elif transformation == "resize":  # Redundant but kept for consistency
            img = img.resize((TARGET_WIDTH, TARGET_HEIGHT))

        # Convert to RGBA for transparency support before drawing
        img = img.convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Use a larger font for better visibility
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

        # Add original text (white, top-left)
        if text:
            draw.text((10, 10), text, font=font, fill="white")

        # Add caption (black, bottom center) with a background rectangle
        if caption:
            caption_text = caption
            bbox = draw.textbbox((0, 0), caption_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (TARGET_WIDTH - text_width) // 2
            text_y = TARGET_HEIGHT - text_height - 20

            # Draw semi-transparent white rectangle behind text
            rect_x0 = text_x - 10
            rect_y0 = text_y - 5
            rect_x1 = text_x + text_width + 10
            rect_y1 = text_y + text_height + 5
            draw.rectangle(
                [(rect_x0, rect_y0), (rect_x1, rect_y1)],
                fill=(255, 255, 255, 128)  # Semi-transparent white
            )

            # Draw black caption text
            draw.text((text_x, text_y), caption_text, font=font, fill="black")

        # Convert back to RGB for saving as JPG
        img = img.convert("RGB")
        temp_image = os.path.join(temp_dir, f"temp_image_{index:02d}.jpg")
        img.save(temp_image)
        print(f"Saved processed image: {temp_image} at {TARGET_WIDTH}x{TARGET_HEIGHT}")
        return temp_image
    except Exception as e:
        print(f"Error in process_image: {str(e)}")
        raise

# Check for audio stream in a file
def check_audio_stream(file_path):
    ffprobe_path = FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe")
    cmd = [ffprobe_path, "-v", "error", "-show_streams", "-select_streams", "a", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if "STREAM" in result.stdout:
        print(f"Audio stream confirmed in {file_path}")
        return True
    print(f"Warning: No audio stream detected in {file_path}")
    return False

# Create video segment with image and audio
def create_image_video_with_audio(image_path, music_path, duration, output_path, start_time, index, temp_dir):
    adjusted_music = adjust_music(music_path, duration, start_time, index, temp_dir)
    cmd = [
        FFMPEG_PATH, "-y", "-loop", "1", "-i", image_path,
        "-i", adjusted_music, "-c:v", "libx264", "-c:a", "mp3",
        "-b:a", "192k", "-map", "0:v:0", "-map", "1:a:0", "-t", str(duration),
        "-pix_fmt", "yuv420p", "-s", f"{TARGET_WIDTH}x{TARGET_HEIGHT}", output_path
    ]
    try:
        print(f"Creating segment with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Created segment: {output_path}\nFFmpeg stdout: {result.stdout}")
        if not check_audio_stream(output_path):
            raise RuntimeError(f"Audio missing in segment {output_path}. FFmpeg stderr: {result.stderr}")
        return adjusted_music
    except subprocess.CalledProcessError as e:
        print(f"Error creating {output_path} - Exit code: {e.returncode}, FFmpeg stderr: {e.stderr}")
        raise

# Concatenate video segments
def concatenate_videos(video_paths, output_path, temp_dir):
    if len(video_paths) == 1:
        shutil.copy(video_paths[0], output_path)
        print(f"Copied single video to: {output_path}")
        return os.path.join(temp_dir, "video_list.txt")
    list_file = os.path.join(temp_dir, "video_list.txt")
    with open(list_file, "w") as f:
        for video in video_paths:
            f.write(f"file '{os.path.abspath(video)}'\n")
    
    cmd = [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Concatenated video: {output_path}\nFFmpeg stdout: {result.stdout}")
        if not check_audio_stream(output_path):
            raise RuntimeError(f"Audio missing in concatenated video {output_path}")
        return list_file
    except subprocess.CalledProcessError as e:
        print(f"Error in concatenate_videos - Exit code: {e.returncode}, FFmpeg stderr: {e.stderr}")
        raise

# Get duration of a file
def get_audio_duration(file_path):
    ffprobe_path = FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe")
    cmd = [
        ffprobe_path, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())
    print(f"Duration of {file_path}: {duration} seconds")
    return duration

# Adjust music for segment
def adjust_music(music_path, duration, start_time, index, temp_dir):
    music_duration = get_audio_duration(music_path)
    adjusted_path = os.path.join(temp_dir, f"adjusted_music_{index:02d}.mp3")
    cmd = [
        FFMPEG_PATH, "-y", "-i", music_path, "-ss", str(start_time),
        "-t", str(duration), "-vn", "-c:a", "mp3", "-b:a", "192k", adjusted_path
    ]
    if start_time + duration > music_duration:
        print(f"Warning: Music {music_path} is shorter ({music_duration}s) than required ({start_time}+{duration}s), looping applied")
        cmd.insert(4, "-stream_loop")
        cmd.insert(5, "-1")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Adjusted music: {adjusted_path}\nFFmpeg stdout: {result.stdout}")
        if not check_audio_stream(adjusted_path):
            raise RuntimeError(f"Adjusted music {adjusted_path} has no audio")
        return adjusted_path
    except subprocess.CalledProcessError as e:
        print(f"Error in adjust_music - Exit code: {e.returncode}, FFmpeg stderr: {e.stderr}")
        raise

# Attach audio to video
def attach_audio_to_video(video_path, audio_path, output_path, duration):
    cmd = [
        FFMPEG_PATH, "-y", 
        "-i", video_path, 
        "-i", audio_path,
        "-c:v", "copy",          # Copy video stream
        "-c:a", "copy",          # Copy MP3 audio directly
        "-map", "0:v:0",         # Map video from first input
        "-map", "1:a:0",         # Map audio from second input
        "-t", str(duration),     # Set duration
        "-pix_fmt", "yuv420p",   # Ensure video compatibility
        output_path
    ]
    try:
        print(f"Attaching audio with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Final video created: {output_path}\nFFmpeg stdout: {result.stdout}\nFFmpeg stderr: {result.stderr}")
        if not check_audio_stream(output_path):
            raise RuntimeError(f"Audio missing in final video {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error in attach_audio_to_video - Exit code: {e.returncode}, FFmpeg stderr: {e.stderr}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Generate a video from images and music with text overlay and caption.")
    parser.add_argument("-i", "--images", nargs="+", required=True, help="Paths to input images.")
    parser.add_argument("-m", "--musics", nargs="+", required=True, help="Paths to music files.")
    parser.add_argument("-t", "--text", help="Text to overlay on images (white, top-left).")
    parser.add_argument("-c", "--caption", required=True, help="Caption text to display (black, bottom center).")
    parser.add_argument("-tr", "--transformation", choices=["grayscale", "rotate", "resize"], required=True, help="Transformation for images.")
    parser.add_argument("-d", "--duration", type=int, default=10, help="Total video duration in seconds.")
    parser.add_argument("-o", "--output", default="final_video.mp4", help="Output video file path.")
    args = parser.parse_args()

    # Check FFmpeg
    try:
        check_ffmpeg()
    except RuntimeError as e:
        print(e)
        return

    # Resolve paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dir = ensure_temp_dir(script_dir)
    try:
        image_paths = [resolve_path(img, script_dir) for img in args.images]
        music_paths = [resolve_path(music, script_dir) for music in args.musics]
    except FileNotFoundError as e:
        print(e)
        return

    text = args.text if args.text else None
    duration_per_image = args.duration / len(image_paths)
    print(f"Duration per image: {duration_per_image} seconds")

    # Process images and create segments
    temp_videos = []
    for i, image_path in enumerate(image_paths):
        music_path = music_paths[i % len(music_paths)]
        start_time = i * duration_per_image
        temp_image = process_image(image_path, text, args.caption, args.transformation, i + 1, temp_dir)
        temp_video = os.path.join(temp_dir, f"segment_{i + 1}.mp4")
        temp_music = create_image_video_with_audio(
            temp_image, music_path, duration_per_image, temp_video, start_time, i + 1, temp_dir
        )
        temp_videos.append(temp_video)

    # Concatenate videos
    concatenated_video = os.path.join(temp_dir, "concatenated.mp4")
    list_file = concatenate_videos(temp_videos, concatenated_video, temp_dir)

    # Extract background music from concatenated video
    extracted_audio = os.path.join(temp_dir, "extracted_audio.mp3")
    cmd_extract = [FFMPEG_PATH, "-y", "-i", concatenated_video, "-vn", "-c:a", "mp3", "-b:a", "192k", extracted_audio]
    result = subprocess.run(cmd_extract, check=True, capture_output=True, text=True)
    print(f"Extracted background music: {extracted_audio}\nFFmpeg stdout: {result.stdout}")
    if not check_audio_stream(extracted_audio):
        raise RuntimeError(f"Extracted audio {extracted_audio} has no audio")

    # Attach extracted music to video
    final_video = args.output
    attach_audio_to_video(concatenated_video, extracted_audio, final_video, args.duration)

    # Verify final video
    final_duration = get_audio_duration(final_video)
    print(f"Video saved to: {os.path.abspath(final_video)} with duration {final_duration}s")

    # Optional: Clean up temp directory (uncomment to enable)
    # shutil.rmtree(temp_dir)
    # print(f"Cleaned up temporary directory: {temp_dir}")

if __name__ == "__main__":
    main()