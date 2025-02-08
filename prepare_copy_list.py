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
    
    for root, _, files in tqdm(os.walk(source_folder), desc="Scanning directories", unit="directory", leave=True):
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

def load_existing_data(output_file):
    """Load existing data from the output file if it exists."""
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            return json.load(f)
    return {"encoder": "", "files": []}

def filter_existing_files(existing_files, file_encoder_map, selected_encoder):
    """Filter existing files to ensure they still qualify for being in the list."""
    valid_files = []
    removed_files_count = 0
    for file_info in tqdm(existing_files, desc="Filtering existing files", unit="file"):
        file_path = file_info["file"]
        file_extension = os.path.splitext(file_path)[1].lower()
        file_encoder = file_encoder_map.get(file_path)

        if os.path.exists(file_path) and file_extension != ".mp4" and (selected_encoder == "any" or file_encoder == selected_encoder):
            valid_files.append(file_info)
        else:
            removed_files_count += 1
    return valid_files, removed_files_count

def main():
    existing_data = load_existing_data(OUTPUT_FILE)
    if existing_data["encoder"]:
        selected_encoder = existing_data["encoder"]
        print(f"Using existing encoder from file: {selected_encoder}")
        video_files = [file_info["file"] for file_info in existing_data["files"]]
        broken_files = []
        file_encoder_map = {file_info["file"]: selected_encoder for file_info in existing_data["files"]}
        existing_data["files"], removed_files_count = filter_existing_files(existing_data["files"], file_encoder_map, selected_encoder)
        print(f"Removed {removed_files_count} files from existing JSON.")
        
        # Flush updated JSON to disk
        with open(OUTPUT_FILE, "w") as f:
            json.dump(existing_data, f, indent=4)
    else:
        selected_encoder = ""
        video_files, broken_files, file_encoder_map = [], [], {}

    source_folder = input("Enter the path to the folder containing video files: ").strip()
    print("Scanning for video files...")

    encoders, new_video_files, new_broken_files, new_file_encoder_map = scan_video_files(source_folder)
    video_files.extend(new_video_files)
    broken_files.extend(new_broken_files)
    file_encoder_map.update(new_file_encoder_map)

    if not selected_encoder:
        selected_encoder = get_encoder_choice(encoders)

    print(f"Filtering files using encoder: {selected_encoder}")
    files_to_process = filter_files(video_files, broken_files, file_encoder_map, selected_encoder.lower())

    existing_data["encoder"] = selected_encoder

    # Add new files to the list if they are not already present
    existing_files_set = {file_info["file"] for file_info in existing_data["files"]}
    for file_info in files_to_process:
        if file_info["file"] not in existing_files_set:
            existing_data["files"].append(file_info)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(existing_data, f, indent=4)

    print(f"List of {len(files_to_process)} files to process saved to {OUTPUT_FILE}")
    print("Processing complete.")

if __name__ == "__main__":
    main()
