import os
import subprocess
import re
import json
from multiprocessing import Pool
from tqdm import tqdm

OUTPUT_FILE = "files_to_process.json"

def get_video_encoder(file_path):
    command = f'ffprobe -v error -show_entries format_tags=encoder -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0 or "Invalid data found" in result.stderr:
        return None
    return result.stdout.strip()

def get_filesize(file):
    try:
        return os.path.getsize(file)  # Get the file size in bytes
    except FileNotFoundError:
        print(f"File not found: {file}")
        return None

def process_video(video_file, selected_encoder):
    encoder = get_video_encoder(video_file)
    if encoder is None or (selected_encoder != "any" and file_encoder.strip().lower() != selected_encoder):
        file_size = get_filesize(video_file)
        if file_size is not None:
            return {"file": video_file, "size": file_size}
    return None

def main():
    source_folder = input("Enter the path to the folder containing video files: ")
    encoders = set()
    video_files = []
    broken_files = []

    for root, _, files in os.walk(source_folder):
        for file in files:
            if re.search(r'(?<!\bEncoded)\.(mp4|mkv|avi|mov|flv|wmv)$', file, re.IGNORECASE):
                video_files.append(os.path.join(root, file))

    print("Finding encoders and files to process. Please wait...")
    with Pool() as p:
        results = list(tqdm(p.imap(process_video, video_files), total=len(video_files)))
      
    encoders = ["Any"] + list(set([res['file'] for res in results if res is not None]))
    print("Encoders found:")
    for idx, encoder in enumerate(encoders):
        print(f"{idx + 1}. {encoder}")

    choice = int(input("Select the encoder to keep (enter the number): ")) - 1
    selected_encoder = encoders[choice].strip().lower()

    files_to_process = [res for res in results if res is not None and res['size'] != 'None']

    with open(OUTPUT_FILE, "w") as f:
        json.dump({"encoder": selected_encoder, "files": files_to_process}, f, indent=4)

    print(f"List of files to process has been saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
