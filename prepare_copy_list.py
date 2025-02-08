import os
import subprocess
import re
import json
from tqdm import tqdm  # Progress bar support

OUTPUT_FILE = "files_to_process.json"
BROKEN_FILE_OUTPUT = "broken_files.json"
VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.mpg')
ENCODER_COMMAND = [
    "ffprobe", "-v", "error",
    "-show_entries", "format_tags=encoder",
    "-of", "default=noprint_wrappers=1:nokey=1"
]

def load_json(file_path):
    """Load existing JSON data, return an empty list if invalid or missing."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"[ERROR] JSON file {file_path} is corrupt. Starting fresh.")
    return []

def save_json(file_path, data):
    """Safely save JSON data."""
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {e}")

def get_video_encoder(file_path):
    """Retrieve the encoder metadata using ffprobe."""
    command = ENCODER_COMMAND + [file_path]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving encoder for {file_path}: {e}")
        return None

def scan_video_files(source_folder):
    """Scan the given folder for video files and retrieve their encoders."""
    encoders = set()
    video_files = []
    broken_files = load_json(BROKEN_FILE_OUTPUT)  # Load existing broken files
    broken_files_map = {bf["file"] for bf in broken_files}
    file_encoder_map = {}
    
    for root, _, files in sorted(os.walk(source_folder), key=lambda x: x[0]):
        print(f"Scanning directory: {root}")
        for file in tqdm(sorted(files), desc=f"Scanning {root}", unit="file", leave=False):
            if re.search(r'\.(mp4|mkv|avi|mov|flv|wmv|webm|mpg)$', file, re.IGNORECASE):
                file_path = os.path.join(root, file)
                if file_path in broken_files_map:
                    continue  # Skip known broken files
                video_files.append(file_path)
                
                encoder = get_video_encoder(file_path)
                if encoder:
                    encoders.add(encoder.strip())
                    file_encoder_map[file_path] = encoder.strip()
                else:
                    broken_files.append({"file": file_path, "size": os.path.getsize(file_path)})
    
    save_json(BROKEN_FILE_OUTPUT, broken_files)  # Update broken files JSON
    return encoders, video_files, file_encoder_map

def filter_files(video_files, file_encoder_map, selected_encoder):
    """Filter files that need processing based on encoder and file type."""
    files_to_process = load_json(OUTPUT_FILE)  # Load existing files to process
    files_to_process_map = {f["file"] for f in files_to_process}

    for file in tqdm(video_files, desc="Filtering", unit="file"):
        file_extension = os.path.splitext(file)[1]
        file_encoder = file_encoder_map.get(file)
        file_size = os.path.getsize(file)

        if file not in files_to_process_map:
            if file_extension == ".mp4" and file_encoder and file_encoder != selected_encoder:
                files_to_process.append({"file": file, "size": file_size})
            elif file_extension != ".mp4":
                files_to_process.append({"file": file, "size": file_size})
    
    save_json(OUTPUT_FILE, files_to_process)  # Save updated files to process

def main():
    source_folder = input("Enter the path to the folder containing video files: ").strip()
    if not os.path.isdir(source_folder):
        print("Invalid source folder path.")
        return

    existing_data = load_json(OUTPUT_FILE)
    selected_encoder = existing_data["encoder"] if "encoder" in existing_data else ""
    print("Scanning for video files...")
    encoders, video_files, file_encoder_map = scan_video_files(source_folder)

    if not selected_encoder:
        if encoders:
            selected_encoder = list(encoders)[0]  # Automatically select first encoder
        else:
            print("No encoders found. Exiting.")
            return

    print(f"Filtering files using encoder: {selected_encoder}")
    filter_files(video_files, file_encoder_map, selected_encoder)
    print(f"Updated list of files to process saved to {OUTPUT_FILE}")
    print(f"Updated list of broken files saved to {BROKEN_FILE_OUTPUT}")
    print("Processing complete.")

if __name__ == "__main__":
    main()
