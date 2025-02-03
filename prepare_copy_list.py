import os
import subprocess
import re
import json
from tqdm import tqdm  # Progress bar support

OUTPUT_FILE = "files_to_process.json"

def get_video_encoder(file_path):
    command = f'ffprobe -v error -show_entries format_tags=encoder -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0 or "Invalid data found" in result.stderr:
        return None
    return result.stdout.strip()

def main():
    source_folder = input("Enter the path to the folder containing video files: ")
    print("Scanning for video files...")
    
    encoders = set()
    video_files = []
    broken_files = []
    file_encoder_map = {}
    
    for root, _, files in os.walk(source_folder):
        print(f"Scanning directory: {root}")  # Printing current directory being scanned
        for file in files:
            if re.search(r'\.(mp4|mkv|avi|mov|flv|wmv)$', file, re.IGNORECASE):
                file_path = os.path.join(root, file)
                video_files.append(file_path)
                encoder = get_video_encoder(file_path)
                if encoder is None:
                    broken_files.append(file_path)
                    print(f"[WARNING] Broken file detected: {file_path}")
                else:
                    encoders.add(encoder)
                    file_encoder_map[file_path] = encoder
    
    encoders = ["Any"] + list(encoders)
    print("\nEncoders found:")
    for idx, encoder in enumerate(encoders):
        print(f"{idx + 1}. {encoder}")
    
    choice = int(input("Select the encoder to keep (enter the number): ")) - 1
    selected_encoder = encoders[choice].strip().lower()
    
    print("Filtering files based on encoder selection...")
    
    files_to_process = []
    for file in tqdm(video_files, desc="Filtering", unit="file"):
        if file in broken_files:
            continue
        file_encoder = file_encoder_map.get(file, None)
        file_extension = file.lower().split('.')[-1]
        if file_extension == "mkv" or (selected_encoder != "any" and file_encoder and file_encoder.strip().lower() != selected_encoder):
            file_size = os.path.getsize(file)  # Get the file size in bytes
            files_to_process.append({"file": file, "size": file_size})
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"encoder": selected_encoder, "files": files_to_process}, f, indent=4)
    
    print(f"List of {len(files_to_process)} files to process has been saved to {OUTPUT_FILE}")
    print("Processing complete.")

if __name__ == "__main__":
    main()
