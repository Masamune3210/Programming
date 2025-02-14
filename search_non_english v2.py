import os
import json
import subprocess
from tqdm import tqdm

def is_non_english_audio(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream_tags=language', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        language = result.stdout.strip()
        return language not in ['eng', 'und']
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def find_non_english_files(folder_path):
    non_english_files = []
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            all_files.append(os.path.join(root, file))
    
    existing_files = set()
    if os.path.exists('non_english_audio.json'):
        with open('non_english_audio.json', 'r') as json_file:
            existing_data = json.load(json_file)
            non_english_files = existing_data.get("files", [])
            existing_files = {file_info["file"] for file_info in non_english_files}
    else:
        with open('non_english_audio.json', 'w') as json_file:
            json_file.write('{"files": [\n')
    
    with open('non_english_audio.json', 'a') as json_file:
        first_entry = len(non_english_files) == 0
        for file_path in tqdm(all_files, desc="Processing files"):
            if file_path not in existing_files and is_non_english_audio(file_path):
                file_info = {
                    "file": file_path,
                    "size": os.path.getsize(file_path)
                }
                if not first_entry:
                    json_file.write(',\n')
                json.dump(file_info, json_file, indent=4)
                json_file.flush()
                first_entry = False
        json_file.write('\n]}')
    
    return non_english_files

def main():
    folder_path = input("Enter the folder path: ")
    non_english_files = find_non_english_files(folder_path)
    print(f"Found {len(non_english_files)} non-English audio files. Results saved to non_english_files.json")

if __name__ == "__main__":
    main()
