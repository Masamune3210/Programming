import os
import subprocess
import re
import json
import shutil

OUTPUT_FILE = "files_to_process.json"
EXTRA_SPACE_REQUIRED = 500 * 1024 * 1024  # 500MB
RETAG_THRESHOLD = 500 * 1024 * 1024  # 500MB
UPDATE_INTERVAL = 10  # Update JSON file every 10 successful removals

def scan_video_files(source_folder):
    encoders = set()
    video_files = []
    broken_files = []
    
    for root, _, files in os.walk(source_folder):
        for file in files:
            if re.search(r'(?<!\bEncoded)\.(mp4|mkv|avi|mov|flv|wmv)$', file, re.IGNORECASE):
                video_files.append(os.path.join(root, file))
    
    for video_file in video_files:
        encoder = get_video_encoder(video_file)
        if encoder is None:
            broken_files.append(video_file)
            print(f"Broken file found: {video_file}")
        else:
            encoders.add(encoder)
    
    return encoders, video_files, broken_files

def get_video_encoder(file_path):
    command = f'ffprobe -v error -show_entries format_tags=encoder -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0 or "Invalid data found" in result.stderr:
        return None
    return result.stdout.strip()

def get_free_space(folder):
    return shutil.disk_usage(folder).free

def save_json(file_list_path, data):
    try:
        with open(file_list_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print("JSON file updated.")
    except Exception as e:
        print(f"Error updating JSON file: {e}")

def copy_files(file_list_path, destination_folder):
    try:
        with open(file_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading JSON file: {e}")
        return

    files_to_copy = data.get("files", [])
    if not files_to_copy:
        print("No files to process.")
        return

    retag_folder = os.path.join(destination_folder, "retag")
    os.makedirs(retag_folder, exist_ok=True)
    
    processed_count = 0
    remaining_files = list(files_to_copy)

    for file_path in files_to_copy[:]:
        if not os.path.exists(file_path):
            print(f"Skipping (not found): {file_path}")
            continue

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        dest_path = os.path.join(retag_folder if file_size < RETAG_THRESHOLD else destination_folder, file_name)

        if os.path.exists(dest_path):
            print(f"Already exists: {file_name}")
            remaining_files.remove(file_path)
            processed_count += 1
        else:
            free_space = get_free_space(destination_folder)
            if free_space < (file_size + EXTRA_SPACE_REQUIRED):
                print(f"Skipping (not enough space): {file_name}")
                continue

            try:
                print(f"Copying: {file_name} → {dest_path}")
                shutil.copy2(file_path, dest_path)
                remaining_files.remove(file_path)
                processed_count += 1
            except Exception as e:
                print(f"Error copying {file_name}: {e}")
                continue

        if processed_count % UPDATE_INTERVAL == 0:
            data["files"] = remaining_files
            save_json(file_list_path, data)

    data["files"] = remaining_files
    save_json(file_list_path, data)
    print("File processing complete.")

def main():
    source_folder = input("Enter the path to the folder containing video files: ")
    encoders, video_files, broken_files = scan_video_files(source_folder)
    
    encoders = ["Any"] + list(encoders)
    print("Encoders found:")
    for idx, encoder in enumerate(encoders):
        print(f"{idx + 1}. {encoder}")
    
    choice = int(input("Select the encoder to keep (enter the number): ")) - 1
    selected_encoder = encoders[choice].strip().lower()
    
    files_to_process = [f for f in video_files if f not in broken_files and (selected_encoder == "any" or get_video_encoder(f).strip().lower() != selected_encoder)]
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"encoder": selected_encoder, "files": files_to_process}, f, indent=4)
    
    print(f"List of files to process saved to {OUTPUT_FILE}")
    
    destination = input("Enter the destination folder: ").strip()
    if not os.path.isdir(destination):
        print("Invalid destination folder.")
    else:
        copy_files(OUTPUT_FILE, destination)

if __name__ == "__main__":
    main()
