import os
import json
import subprocess
from tqdm import tqdm

LOG_FILE = "non_english_audio.json"

def load_existing_log():
    """Loads the existing JSON log file if it exists, otherwise returns an empty structure."""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"files": []}
    return {"files": []}

def save_log(log_data):
    """Writes and flushes the log data to the JSON file."""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=4)
        f.flush()

def get_audio_languages(file_path):
    """Runs ffprobe to get the language of audio tracks in a media file."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-select_streams", "a",
        file_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        streams = json.loads(result.stdout).get("streams", [])

        languages = {stream.get("tags", {}).get("language", "und") for stream in streams}

        return languages
    except subprocess.CalledProcessError as e:
        tqdm.write(f"\nError processing {file_path}: {e}")
        return set()
    except json.JSONDecodeError:
        tqdm.write(f"\nInvalid JSON output from ffprobe for {file_path}")
        return set()

def scan_directory(root_folder):
    """Walks through directories and checks each media file for non-English audio."""
    log_data = load_existing_log()
    logged_files = {entry["file"] for entry in log_data["files"]}  # Set for quick lookup
    all_files = []

    # Collect all media files first for tqdm progress bar
    for dirpath, _, filenames in os.walk(root_folder):
        for file in filenames:
            if file.lower().endswith((".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv")):
                all_files.append(os.path.join(dirpath, file))

    if not all_files:
        print("No media files found in the given directory.")
        return

    current_dir = ""
    try:
        with tqdm(total=len(all_files), desc="Processing files", unit="file") as pbar:
            for file_path in all_files:
                new_dir = os.path.dirname(file_path)
                if new_dir != current_dir:
                    current_dir = new_dir
                    tqdm.write(f"Scanning: {current_dir}")  # Print above progress bar

                if file_path in logged_files:
                    pbar.update(1)
                    continue  # Skip already logged files

                languages = get_audio_languages(file_path)

                # Ignore files with only undefined audio
                if not languages or languages == {"und"}:
                    pbar.update(1)
                    continue

                # Log files that do not contain English audio
                if "eng" not in languages:
                    file_size = os.path.getsize(file_path)
                    log_entry = {"file": file_path, "size": file_size}

                    tqdm.write(f"Non-English audio found: {file_path} (Languages: {', '.join(languages)})")
                    log_data["files"].append(log_entry)
                    logged_files.add(file_path)

                    save_log(log_data)  # Save immediately to avoid data loss

                pbar.update(1)  # Update tqdm progress bar

    except KeyboardInterrupt:
        print("\nScan interrupted by user. Progress has been saved.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")

if __name__ == "__main__":
    folder = input("Enter the folder to scan: ").strip()
    if os.path.isdir(folder):
        scan_directory(folder)
    else:
        print("Invalid folder path.")
