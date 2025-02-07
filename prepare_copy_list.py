import os
import subprocess
import re
import json
from tqdm import tqdm  # Progress bar support

OUTPUT_FILE = "files_to_process.json"

def get_video_encoder(file_path):
    """Retrieve the encoder metadata using ffprobe."""
    command = [
        "ffprobe", "-v", "error",
        "-show_entries", "format_tags=encoder",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0 or result.stderr:
        return None  # Failed to retrieve encoder

    return result.stdout.strip()

def scan_video_files(source_folder):
    """Scan the given folder for video files and retrieve their encoders."""
    encoders = set()
    video_files = []
    broken_files = []
    file_encoder_map = {}
    
    for root, _, files in os.walk(source_folder):
        print(f"Scanning directory: {root}")
        for file in files:
            if re.search(r'\.(mp4|mkv|avi|mov|flv|wmv)$', file, re.IGNORECASE):
                file_path = os.path.join(root, file)
                video_files.append(file_path)

                encoder = get_video_encoder(file_path)
                if encoder is None:
                    broken_files.append(file_path)
                    print(f"[WARNING] Broken file detected: {file_path}")
                else:
                    encoders.add(encoder.strip().lower())
                    file_encoder_map[file_path] = encoder.strip().lower()

    return encoders, video_files, broken_files, file_encoder_map

def get_encoder_choice(encoders):
    """Prompt the user to select an encoder to filter files."""
    encoders = ["Any"] + sorted(encoders)  # Include "Any" and sort the list
    print("\nEncoders found:")
    for idx, encoder in enumerate(encoders, start=1):
        print(f"{idx}. {encoder}")

    while True:
        try:
            choice = int(input("Select the encoder to keep (enter the number): ")) - 1
            if 0 <= choice < len(encoders):
                return encoders[choice]
            print("Invalid selection. Please enter a valid number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def filter_files(video_files, broken_files, file_encoder_map, selected_encoder):
    """Filter files that need processing based on encoder and file type."""
    files_to_process = []

    for file in tqdm(video_files, desc="Filtering", unit="file"):
        if file in broken_files:
            continue  # Skip broken files
        
        file_extension = os.path.splitext(file)[1].lower()
        file_encoder = file_encoder_map.get(file)

        if file_extension != ".mp4" or (selected_encoder != "any" and file_encoder and file_encoder != selected_encoder):
            file_size = os.path.getsize(file)  # Get file size in bytes
            files_to_process.append({"file": file, "size": file_size})

    return files_to_process

def main():
    source_folder = input("Enter the path to the folder containing video files: ").strip()
    print("Scanning for video files...")

    encoders, video_files, broken_files, file_encoder_map = scan_video_files(source_folder)
    selected_encoder = get_encoder_choice(encoders)

    print(f"Filtering files using encoder: {selected_encoder}")
    files_to_process = filter_files(video_files, broken_files, file_encoder_map, selected_encoder.lower())

    with open(OUTPUT_FILE, "w") as f:
        json.dump({"encoder": selected_encoder, "files": files_to_process}, f, indent=4)

    print(f"List of {len(files_to_process)} files to process saved to {OUTPUT_FILE}")
    print("Processing complete.")

if __name__ == "__main__":
    main()
