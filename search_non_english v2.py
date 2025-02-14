import os
import json
import subprocess

def is_non_english_audio(file_path):
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'stream_tags=language', '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        language = result.stdout.strip()
        return language != 'eng'
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def find_non_english_files(folder_path):
    non_english_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            if is_non_english_audio(file_path):
                file_info = {
                    "file": file_path,
                    "size": os.path.getsize(file_path)
                }
                non_english_files.append(file_info)
    return non_english_files

def main():
    folder_path = input("Enter the folder path: ")
    non_english_files = find_non_english_files(folder_path)
    with open('non_english_files.json', 'w') as json_file:
        json.dump({"files": non_english_files}, json_file, indent=4)
    print(f"Found {len(non_english_files)} non-English audio files. Results saved to non_english_files.json")

if __name__ == "__main__":
    main()
