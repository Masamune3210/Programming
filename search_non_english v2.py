import os
import json
import subprocess
from tqdm import tqdm

def is_non_english_audio(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream_tags=language', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        languages = result.stdout.strip().split('\n')
        return all(language not in ['eng', 'und'] for language in languages)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def is_media_file(file_path):
    media_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.mpg', '.mpeg', '.mov', '.3gp', '.webm'}
    return os.path.splitext(file_path)[1].lower() in media_extensions

def find_non_english_files(folder_path):
    non_english_files = []
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            if is_media_file(file_path):
                all_files.append(file_path)
    
    existing_files = set()
    if os.path.exists('non_english_audio.json'):
        try:
            with open('non_english_audio.json', 'r') as json_file:
                existing_data = json.load(json_file)
                non_english_files = existing_data.get("files", [])
                existing_files = {file_info["file"] for file_info in non_english_files}
        except json.JSONDecodeError:
            print("Error reading JSON file. Assuming the file is damaged and overwriting it.")
            existing_data = {"files": []}
    else:
        existing_data = {"files": []}
    
    for file_path in tqdm(all_files, desc="Processing files"):
        if file_path not in existing_files and is_non_english_audio(file_path):
            file_info = {
                "file": file_path,
                "size": os.path.getsize(file_path)
            }
            non_english_files.append(file_info)
            existing_data["files"].append(file_info)
            with open('non_english_audio.json', 'w') as json_file:
                json.dump(existing_data, json_file, indent=4)
                json_file.flush()
    
    return non_english_files

def main():
    folder_path = input("Enter the folder path: ")
    non_english_files = find_non_english_files(folder_path)
    print(f"Found {len(non_english_files)} non-English audio files. Results saved to non_english_audio.json")

if __name__ == "__main__":
    main()
