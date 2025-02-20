import os
import sys
import signal
import subprocess
import shutil
import psutil  # For force killing HandBrakeCLI if needed
import re
from tqdm import tqdm
import send2trash  # Add send2trash for sending files to recycle bin
import time
import msvcrt  # For detecting keyboard strokes on Windows

# Configurable settings
HANDBRAKECLI_DEFAULT_PATH = r"C:\\Tools\\handbrakecli"
PRESETS = {
    "kids": "1080p Kids",
    "2160": "4k hdr3",
    "default": "1080p4"
}
EXCLUDED_DIRS = ["more", "retag", "$RECYCLE.BIN", "System Volume Information", "errored", "non-eng"]
GAME_FOLDERS = ["D:\\Games", "E:\\Games", "D:\\GOG Games", "D:\\XboxGames",
                 "F:\\Emulation\\Emulators", "F:\\Games", "F:\\XboxGames", "G:\\Games",
                   "G:\\SteamLibrary", "G:\\XboxGames"]  # Add paths to game folders here

current_output_file = None
current_process = None  # Track HandBrakeCLI process

def find_handbrakecli():
    handbrakecli_path = HANDBRAKECLI_DEFAULT_PATH
    if not os.path.exists(handbrakecli_path):
        handbrakecli_path = input("HandBrakeCLI not found at default location. Please provide the full path: ")
        if not os.path.exists(handbrakecli_path):
            print("HandBrakeCLI not found. Exiting.")
            sys.exit(1)
    return handbrakecli_path

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

def cleanup_on_exit(signal, frame):
    """Cleanup function for interruptions."""
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

signal.signal(signal.SIGINT, cleanup_on_exit)

def parse_progress(line):
    """Extracts encoding progress from HandBrakeCLI output."""
    match = re.search(r'Encoding: task \d+ of \d+, (\d+\.\d+) %', line)
    return float(match.group(1)) if match else None

def encode_video(input_file, output_file, preset_name, handbrakecli_path):
    global current_output_file, current_process
    current_output_file = output_file

    command = [
        os.path.join(handbrakecli_path, "HandBrakeCLI.exe"),
        "--preset-import-gui",
        "-Z", preset_name,
        "-i", input_file,
        "-o", output_file,
    ]

    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding="utf-8", errors="replace") as process:
            current_process = process
            progress_bar = tqdm(total=100, unit="%", desc="Encoding Progress", ncols=80, dynamic_ncols=True, position=0, leave=True)
            last_progress = 0

            for line in process.stdout:
                # We suppress output except for progress updates
                progress = parse_progress(line)
                if progress is not None:
                    progress_bar.update(progress - last_progress)
                    last_progress = progress

            progress_bar.close()
            process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

        print(f"Encoding complete: {output_file}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error encoding video {input_file}: {e}")
        return False

def check_audio_tracks(file_path):
    """Check if the file has at least one audio track using ffprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        file_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return bool(result.stdout.strip())

def handle_file(input_file, output_file, source_folder):
    if os.path.exists(output_file):
        input_size = os.path.getsize(input_file)
        output_size = os.path.getsize(output_file)

        print(f"Size Check - Input: {input_size / (1024 * 1024):.2f} MB | Output: {output_size / (1024 * 1024):.2f} MB")

        if output_size < input_size and check_audio_tracks(output_file):
            send2trash.send2trash(input_file)
            print(f"✅ Sent input file to recycle bin {input_file} (output is smaller and has audio).")
        else:
            if not check_audio_tracks(output_file):
                send2trash.send2trash(output_file)
                handle_encoding_error(input_file, source_folder)
                print(f"⚠️ Output has no audio. Moved {input_file} to 'errored' folder for review.")
            else:
                send2trash.send2trash(output_file)
                retag_folder = os.path.join(source_folder, "retag")
                os.makedirs(retag_folder, exist_ok=True)
                shutil.move(input_file, os.path.join(retag_folder, os.path.basename(input_file)))
                print(f"⚠️ Output is not smaller. Moved {input_file} to 'retag' folder for review.")
def handle_encoding_error(input_file, source_folder):
    errored_folder = os.path.join(source_folder, "errored")
    os.makedirs(errored_folder, exist_ok=True)
    shutil.move(input_file, os.path.join(errored_folder, os.path.basename(input_file)))
    print(f"Encoding error. Moved {input_file} to 'errored' folder.")

def get_preset_for_file(file_path, source_folder):
    relative_path = os.path.relpath(file_path, source_folder)
    folder_name = os.path.dirname(relative_path).lower()

    if folder_name == "kids":
        return PRESETS["kids"]
    elif folder_name == "2160":
        return PRESETS["2160"]
    else:
        return PRESETS["default"]

def is_game_running():
    """Check if any executable from the specified game folders is running."""
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            if proc.info['exe']:
                for game_folder in GAME_FOLDERS:
                    if proc.info['exe'].startswith(game_folder):
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def wait_for_game_exit():
    """Wait for the game to exit or for the user to press 'c' to continue."""
    print("\nGame detected. Pausing processing... Press 'c' to continue anyway.")
    while is_game_running():
        if msvcrt.kbhit() and msvcrt.getch().lower() == b'c':
            print("\nContinuing processing despite game running.")
            break
        time.sleep(1)  # Check every second
    else:
        print("\nGame exited. Resuming processing...")

def process_folder(source_folder, destination_folder, handbrakecli_path):
    os.makedirs(destination_folder, exist_ok=True)

    all_files = []
    for root, dirs, files in os.walk(source_folder):
        for d in EXCLUDED_DIRS:
            if d in dirs:
                dirs.remove(d)
        
        for filename in files:
            if filename.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                file_path = os.path.join(root, filename)
                file_size = os.path.getsize(file_path)
                all_files.append((file_path, file_size))

    if not all_files:
        print("No files found to process.")
        return False

    # Separate non-MP4 and MP4 files
    non_mp4_files = [file for file in all_files if not file[0].lower().endswith('.mp4')]
    mp4_files = [file for file in all_files if file[0].lower().endswith('.mp4')]

    # Sort files by size (smallest first)
    non_mp4_files.sort(key=lambda x: x[1])
    mp4_files.sort(key=lambda x: x[1])

    file_progress = tqdm(total=len(all_files), desc="Total Progress", unit="file", ncols=80, dynamic_ncols=True, position=0, leave=True)

    # Process non-MP4 files first
    for file_path, _ in non_mp4_files:
        if is_game_running():
            wait_for_game_exit()

        filename = os.path.basename(file_path)
        preset_name = get_preset_for_file(file_path, source_folder)
        output_file = os.path.join(destination_folder, os.path.splitext(filename)[0] + ".mp4")
        print(f"\nProcessing: {filename} - {preset_name}")

        if encode_video(file_path, output_file, preset_name, handbrakecli_path):
            handle_file(file_path, output_file, source_folder)
        else:
            handle_encoding_error(file_path, source_folder)

        file_progress.update(1)

    # Process MP4 files next
    for file_path, _ in mp4_files:
        if is_game_running():
            wait_for_game_exit()

        filename = os.path.basename(file_path)
        preset_name = get_preset_for_file(file_path, source_folder)
        output_file = os.path.join(destination_folder, filename)
        print(f"\nProcessing: {filename} - {preset_name}")

        if encode_video(file_path, output_file, preset_name, handbrakecli_path):
            handle_file(file_path, output_file, source_folder)
        else:
            handle_encoding_error(file_path, source_folder)

        file_progress.update(1)

    file_progress.close()

    return True

def main():
    source_folder = input("Enter the source folder path: ")
    destination_folder = input("Enter the destination folder path: ")
    if not os.path.exists(source_folder):
        print("Source folder does not exist. Exiting.")
        sys.exit(1)

    handbrakecli_path = find_handbrakecli()

    while True:
        if is_game_running():
            wait_for_game_exit()

        if not process_folder(source_folder, destination_folder, handbrakecli_path):
            print("No new files found. Exiting.")
            return True

        print("Waiting for new files to process...")
        time.sleep(60)  # Wait for 60 seconds before scanning the folder again

if __name__ == "__main__":
    main()