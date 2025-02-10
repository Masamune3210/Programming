import os
import sys
import subprocess
import shutil
import re
import psutil
import signal
import send2trash
from tqdm import tqdm

# Configurable settings
HANDBRAKECLI_PATH = r"C:\\Tools\\handbrakecli"
MP4TAG_PATH = r"C:\\Tools\\mp4tag\\mp4tag.exe"
TOOL_TEXT = "HandBrake 1.9.0 2024120100"
PRESETS = {"kids": "1080p Kids", "2160": "4k hdr3", "default": "1080p4"}
SUPPORTED_EXTENSIONS = ('.mkv', '.webm', '.avi', '.mpg')
FAILED_FOLDER_NAME = "failedconv"
RETAG_FOLDER_NAME = "retag"
EXCLUDED_DIRS = ["more", "$RECYCLE.BIN", "System Volume Information", "errored"]

current_output_file = None
current_process = None

def find_handbrakecli():
    if not os.path.exists(HANDBRAKECLI_PATH):
        print("HandBrakeCLI not found. Exiting.")
        sys.exit(1)
    return HANDBRAKECLI_PATH

def parse_progress(line):
    match = re.search(r'Encoding: task \d+ of \d+, (\d+\.\d+) %', line)
    return float(match.group(1)) if match else None

def encode_video(input_file, output_file, preset_name, handbrakecli_path):
    global current_output_file, current_process
    current_output_file = output_file
    command = [
        os.path.join(handbrakecli_path, "HandBrakeCLI.exe"),
        "--preset-import-gui", "-Z", preset_name,
        "-i", input_file, "-o", output_file,
    ]
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as process:
            current_process = process
            progress_bar = tqdm(total=100, unit="%", desc="Encoding Progress")
            last_progress = 0
            for line in process.stdout:
                progress = parse_progress(line)
                if progress is not None:
                    progress_bar.update(progress - last_progress)
                    last_progress = progress
            progress_bar.close()
        return process.returncode == 0
    except subprocess.CalledProcessError:
        return False

def convert_to_mp4(input_file, output_file):
    command = ["ffmpeg", "-fflags", "+genpts", "-i", input_file, "-c:v", "copy", "-c:a", "copy", "-map", "0:v", "-map", "0:a", output_file]
    try:
        subprocess.run(command, check=True, stderr=subprocess.PIPE)
        return verify_file_with_ffprobe(output_file)
    except subprocess.CalledProcessError:
        return False

def verify_file_with_ffprobe(file_path):
    command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0 and result.stdout.strip() != b''

def tag_mp4(file_path):
    command = [MP4TAG_PATH, '--set', f'Tool:S:{TOOL_TEXT}', file_path]
    try:
        subprocess.run(command, check=True)
        print(f"Tagged: {file_path}")
    except subprocess.CalledProcessError:
        print(f"Failed to tag: {file_path}")

def cleanup_on_exit(signal, frame):
    global current_output_file, current_process
    print("\nProcess interrupted. Cleaning up...")

    if current_process:
        print(f"Attempting to terminate HandBrakeCLI (PID: {current_process.pid})...")
        try:
            current_process.terminate()
            current_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Process did not terminate in time. Forcing kill...")
            kill_process(current_process)

    if current_output_file and os.path.exists(current_output_file):
        try:
            send2trash.send2trash(current_output_file)
            print(f"Sent partially encoded file to recycle bin: {current_output_file}")
        except Exception as e:
            print(f"Error sending partial file to recycle bin: {e}")

    sys.exit(0)

def kill_process(process):
    if process is None:
        return
    
    try:
        proc = psutil.Process(process.pid)
        for child in proc.children(recursive=True):
            child.kill()
        proc.kill()
        proc.wait(5)
        print(f"Forcefully killed HandBrakeCLI (PID: {process.pid})")
    except psutil.NoSuchProcess:
        print("HandBrakeCLI process already terminated.")
    except Exception as e:
        print(f"Error killing HandBrakeCLI: {e}")

signal.signal(signal.SIGINT, cleanup_on_exit)

def process_folder(source_folder, destination_folder, handbrakecli_path):
    os.makedirs(destination_folder, exist_ok=True)
    os.makedirs(os.path.join(source_folder, RETAG_FOLDER_NAME), exist_ok=True)
    allowed_folders = {"2160", "kids", ""}
    non_mp4_files = []
    mp4_files = []
    for root, _, files in os.walk(source_folder):
        relative_path = os.path.relpath(root, source_folder)
        if relative_path == ".":
            relative_path = ""
        if relative_path.split(os.sep)[0] in allowed_folders:
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                if file.lower().endswith(SUPPORTED_EXTENSIONS):
                    non_mp4_files.append((file_path, file_size))
                elif file.lower().endswith('.mp4'):
                    mp4_files.append((file_path, file_size))
    non_mp4_files.sort(key=lambda x: x[1])
    mp4_files.sort(key=lambda x: x[1])
    all_files = non_mp4_files + mp4_files
    for file_path, _ in tqdm(all_files, desc="Processing Files"):
        filename = os.path.basename(file_path)
        preset_name = PRESETS.get("2160" if "2160" in file_path else "kids" if "kids" in file_path else "default")
        output_file = os.path.join(destination_folder, os.path.splitext(filename)[0] + ".mp4")
        if encode_video(file_path, output_file, preset_name, handbrakecli_path):
            input_size = os.path.getsize(file_path)
            output_size = os.path.getsize(output_file)
            print(f"Size Check - Input: {input_size / (1024 * 1024):.2f} MB | Output: {output_size / (1024 * 1024):.2f} MB")
            if output_size < input_size:
                send2trash.send2trash(file_path)
                print(f"✅ Sent input file to recycle bin {file_path} (output is smaller).")
            else:
                send2trash.send2trash(output_file)
                retag_folder = os.path.join(source_folder, RETAG_FOLDER_NAME)
                shutil.move(file_path, os.path.join(retag_folder, filename))
                print(f"⚠️ Output is not smaller. Moved {file_path} to 'retag' folder for review.")

                # Handle conversion and tagging immediately
                if not file_path.lower().endswith('.mp4'):
                    converted_file = os.path.join(retag_folder, os.path.splitext(filename)[0] + ".mp4")
                    if convert_to_mp4(os.path.join(retag_folder, filename), converted_file):
                        send2trash.send2trash(os.path.join(retag_folder, filename))
                        tag_mp4(converted_file)
                    else:
                        print(f"Failed to convert: {filename}")
                        continue  # Skip to the next file if conversion fails
                else:
                    tag_mp4(file_path)
        else:
            print(f"Failed to encode: {file_path}")

def main():
    source_folder = input("Enter the source folder path: ")
    destination_folder = input("Enter the destination folder path: ")
    if not os.path.exists(source_folder):
        print("Source folder does not exist. Exiting.")
        sys.exit(1)
    handbrakecli_path = find_handbrakecli()
    process_folder(source_folder, destination_folder, handbrakecli_path)

if __name__ == "__main__":
    main()