import os
import subprocess
import shutil
import re
import json

BOOKMARK_FILE = "bookmark.json"

def get_video_encoder(file_path):
    command = f'ffprobe -v error -show_entries format_tags=encoder -of default=noprint_wrappers=1:nokey=1 "{file_path}"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0 or "Invalid data found" in result.stderr:
        return None
    return result.stdout.strip()

def has_enough_space(destination_folder, file_path, buffer=500 * 1024 * 1024):
    total, used, free = shutil.disk_usage(destination_folder)
    file_size = os.path.getsize(file_path)
    return free >= file_size + buffer

def file_exists_in_destination(destination_folder, file_name):
    return os.path.exists(os.path.join(destination_folder, file_name))

def load_bookmark(destination_folder):
    bookmark_path = os.path.join(destination_folder, BOOKMARK_FILE)
    if os.path.exists(bookmark_path):
        with open(bookmark_path, "r") as f:
            return json.load(f)
    return None

def save_bookmark(destination_folder, bookmark):
    bookmark_path = os.path.join(destination_folder, BOOKMARK_FILE)
    with open(bookmark_path, "w") as f:
        json.dump(bookmark, f, indent=4)

def main():
    source_folder = input("Enter the path to the folder containing video files: ")
    destination_folder = input("Enter the path to the destination folder: ")

    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    retag_folder = os.path.join(destination_folder, "retag")
    if not os.path.exists(retag_folder):
        os.makedirs(retag_folder)

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

    encoders = ["Any"] + list(encoders)
    print("Encoders found:")
    for idx, encoder in enumerate(encoders):
        print(f"{idx + 1}. {encoder}")

    choice = int(input("Select the encoder to keep (enter the number): ")) - 1
    selected_encoder = encoders[choice].strip().lower()

    bookmark = load_bookmark(destination_folder)
    if bookmark:
        processed_files = set(bookmark["processed"])
        remaining_files = bookmark["remaining"]
        selected_encoder = bookmark["encoder"]
        print(f"Resuming from bookmark with encoder: {selected_encoder}")
    else:
        processed_files = set()
        remaining_files = video_files.copy()
        bookmark = {"encoder": selected_encoder, "processed": list(processed_files), "remaining": remaining_files}
        save_bookmark(destination_folder, bookmark)

    counter = 0
    for video_file in remaining_files[:]:
        if video_file in broken_files or video_file in processed_files:
            continue

        file_name = os.path.basename(video_file)
        file_size = os.path.getsize(video_file)
        file_extension = file_name.lower().split('.')[-1]
        encoder = get_video_encoder(video_file)
        encoder = encoder.strip().lower() if encoder else ""

        if file_extension == "mkv":
            if file_exists_in_destination(destination_folder, file_name):
                print(f"Skipped MKV file because it already exists: {file_name}")
                continue
            if has_enough_space(destination_folder, video_file):
                shutil.copy(video_file, os.path.join(destination_folder, file_name))
                print(f"Copied MKV file: {video_file}")
                processed_files.add(video_file)
                remaining_files.remove(video_file)
            else:
                print(f"Skipped MKV file due to insufficient space: {video_file}")
            continue

        if file_size < 500 * 1024 * 1024 and (selected_encoder == "any" or encoder != selected_encoder):
            if file_exists_in_destination(retag_folder, file_name):
                print(f"Skipped small file because it already exists: {file_name}")
                continue
            if has_enough_space(destination_folder, video_file):
                shutil.copy(video_file, os.path.join(retag_folder, file_name))
                print(f"Copied small file to 'retag': {video_file}")
                processed_files.add(video_file)
                remaining_files.remove(video_file)
            else:
                print(f"Skipped small file due to insufficient space: {video_file}")
            continue

        if selected_encoder == "any" or encoder != selected_encoder:
            if file_exists_in_destination(destination_folder, file_name):
                print(f"Skipped file because it already exists: {file_name}")
                continue
            if has_enough_space(destination_folder, video_file):
                shutil.copy(video_file, os.path.join(destination_folder, file_name))
                print(f"Copied file: {video_file}")
                processed_files.add(video_file)
                remaining_files.remove(video_file)

        counter += 1
        if counter % 30 == 0:
            print(f"Processed {counter} files so far...")
            bookmark["processed"] = list(processed_files)
            bookmark["remaining"] = remaining_files
            save_bookmark(destination_folder, bookmark)

    bookmark_path = os.path.join(destination_folder, BOOKMARK_FILE)
    if os.path.exists(bookmark_path):
        os.remove(bookmark_path)

    print("Process completed.")

if __name__ == "__main__":
    main()
