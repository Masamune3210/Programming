import os
import sys
import signal
import subprocess
import shutil
import psutil  # For force killing HandBrakeCLI if needed
import re
from tqdm import tqdm

current_output_file = None
current_process = None  # Track HandBrakeCLI process

def find_handbrakecli():
    handbrakecli_path = r"C:\Tools\handbrakecli"
    if not os.path.exists(handbrakecli_path):
        handbrakecli_path = input("HandBrakeCLI not found at default location. Please provide the full path: ")
        if not os.path.exists(handbrakecli_path):
            print("HandBrakeCLI not found. Exiting.")
            sys.exit(1)
    return handbrakecli_path

def kill_process(process):
    #Forcefully kill a process and its children.
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
            os.remove(current_output_file)
            print(f"Deleted partially encoded file: {current_output_file}")
        except Exception as e:
            print(f"Error deleting partial file: {e}")

    sys.exit(0)

signal.signal(signal.SIGINT, cleanup_on_exit)

def parse_progress(line):
    """Extracts encoding progress from HandBrakeCLI output."""
    match = re.search(r'Encoding: task \d+ of \d+, (\d+\.\d+) %', line)
    return float(match.group(1)) if match else None

def encode_video(input_file, output_file, preset_file, handbrakecli_path):
    global current_output_file, current_process
    current_output_file = output_file

    command = [
        os.path.join(handbrakecli_path, "HandBrakeCLI.exe"),
        "--preset-import-file", preset_file,
        "-i", input_file,
        "-o", output_file,
    ]

    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
            current_process = process
            progress_bar = tqdm(total=100, unit="%", desc="Encoding Progress", ncols=80)

            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()

                progress = parse_progress(line)
                if progress is not None:
                    progress_bar.n = progress
                    progress_bar.refresh()

            progress_bar.close()

            process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)

        print(f"Encoding complete: {output_file}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error encoding video {input_file}: {e}")
        return False

def handle_file(input_file, output_file, source_folder):
    if os.path.exists(output_file):
        input_size = os.path.getsize(input_file)
        output_size = os.path.getsize(output_file)

        if output_size < input_size:
            os.remove(input_file)
            print(f"Deleted input file {input_file} (output is smaller).")
        else:
            os.remove(output_file)
            retag_folder = os.path.join(source_folder, "retag")
            os.makedirs(retag_folder, exist_ok=True)
            shutil.move(input_file, os.path.join(retag_folder, os.path.basename(input_file)))
            print(f"Output is not smaller. Moved {input_file} to 'retag' folder.")

def handle_encoding_error(input_file, source_folder):
    errored_folder = os.path.join(source_folder, "errored")
    os.makedirs(errored_folder, exist_ok=True)
    shutil.move(input_file, os.path.join(errored_folder, os.path.basename(input_file)))
    print(f"Encoding error. Moved {input_file} to 'errored' folder.")

def get_preset_for_file(file_path, source_folder):
    relative_path = os.path.relpath(file_path, source_folder)
    folder_name = os.path.dirname(relative_path).lower()

    if folder_name == "kids":
        return "kids.json"
    elif folder_name == "2160":
        return "4k.json"
    else:
        return "1080.json"

def process_folder(source_folder, destination_folder, preset_files, handbrakecli_path):
    os.makedirs(destination_folder, exist_ok=True)

    for root, dirs, files in os.walk(source_folder):
        for d in ["more", "retag"]:
            if d in dirs:
                dirs.remove(d)

        for filename in files:
            if filename.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                file_path = os.path.join(root, filename)
                preset_file = get_preset_for_file(file_path, source_folder)

                if preset_file not in preset_files:
                    print(f"Preset file '{preset_file}' not found. Exiting.")
                    sys.exit(1)

                preset_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), preset_file)
                if not os.path.exists(preset_path):
                    print(f"Preset file '{preset_file}' does not exist. Exiting.")
                    sys.exit(1)

                output_file = os.path.join(destination_folder, filename)
                print(f"Processing: {filename}")

                if encode_video(file_path, output_file, preset_path, handbrakecli_path):
                    handle_file(file_path, output_file, source_folder)
                else:
                    handle_encoding_error(file_path, source_folder)

def main():
    script_directory = os.path.dirname(os.path.realpath(__file__))
    preset_files = [f for f in os.listdir(script_directory) if f.endswith('.json') and f != 'files_to_process.json']

    if not preset_files:
        print("No preset files found. Exiting.")
        sys.exit(1)

    source_folder = input("Enter the source folder path: ")
    destination_folder = input("Enter the destination folder path: ")

    if not os.path.exists(source_folder):
        print("Source folder does not exist. Exiting.")
        sys.exit(1)

    handbrakecli_path = find_handbrakecli()
    process_folder(source_folder, destination_folder, preset_files, handbrakecli_path)

if __name__ == "__main__":
    main()
