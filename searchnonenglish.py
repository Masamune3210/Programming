import os
import json
import subprocess
from tqdm import tqdm

LOG_FILE = "non_english_audio.log"

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
        
        languages = set()
        for stream in streams:
            lang = stream.get("tags", {}).get("language", "und")  # Default to "und" if not found
            languages.add(lang)
        
        return languages
    except subprocess.CalledProcessError as e:
        tqdm.write(f"\nError processing {file_path}: {e}")
        return set()
    except json.JSONDecodeError:
        tqdm.write(f"\nInvalid JSON output from ffprobe for {file_path}")
        return set()

def scan_directory(root_folder):
    """Walks through directories and checks each media file for non-English audio."""
    non_english_files = set()
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
        with open(LOG_FILE, "a", encoding="utf-8") as log_file, tqdm(total=len(all_files), desc="Processing files", unit="file") as pbar:
            for file_path in all_files:
                new_dir = os.path.dirname(file_path)
                if new_dir != current_dir:
                    current_dir = new_dir
                    tqdm.write(f"Scanning: {current_dir}")  # Print above progress bar

                languages = get_audio_languages(file_path)
                if languages and "eng" not in languages:
                    log_entry = f"{file_path} (Languages: {', '.join(languages)})\n"
                    if log_entry not in non_english_files:
                        tqdm.write(f"Non-English audio found: {file_path} (Languages: {', '.join(languages)})")
                        non_english_files.add(log_entry)
                        log_file.write(log_entry)
                        log_file.flush()  # Flush to ensure progress is saved

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
