import json
import os
import subprocess
import shutil

def get_user_input():
    json_file = input("Enter the path to the JSON file: ")
    dest_folder = input("Enter the destination folder: ")
    return json_file, dest_folder

def load_json(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
    return data

def remux_file(file_path, output_path):
    command = ['ffmpeg', '-i', file_path, '-c', 'copy', output_path]
    result = subprocess.run(command, capture_output=True)
    return result.returncode == 0

def reencode_audio(file_path, output_path):
    command = ['ffmpeg', '-i', file_path, '-c:v', 'copy', '-c:a', 'aac', output_path]
    result = subprocess.run(command, capture_output=True)
    return result.returncode == 0

def check_file(file_path):
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    result = subprocess.run(command, capture_output=True)
    return result.returncode == 0

def process_files(file_list, dest_folder):
    remuxed_folder = os.path.join(dest_folder, 'remuxed')
    reencoded_folder = os.path.join(dest_folder, 'reencoded')
    unrepaired_folder = os.path.join(dest_folder, 'unrepaired')
    fixed_folder = os.path.join(dest_folder, 'fixed')
    os.makedirs(remuxed_folder, exist_ok=True)
    os.makedirs(reencoded_folder, exist_ok=True)
    os.makedirs(unrepaired_folder, exist_ok=True)
    os.makedirs(fixed_folder, exist_ok=True)

    for file_path in file_list:
        file_name = os.path.basename(file_path)
        remuxed_path = os.path.join(remuxed_folder, file_name)
        reencoded_path = os.path.join(reencoded_folder, file_name)

        if remux_file(file_path, remuxed_path) and check_file(remuxed_path):
            shutil.move(remuxed_path, os.path.join(fixed_folder, file_name))
            os.remove(file_path)
            print(f"Successfully remuxed and fixed: {file_name}")
        elif reencode_audio(file_path, reencoded_path) and check_file(reencoded_path):
            shutil.move(reencoded_path, os.path.join(fixed_folder, file_name))
            os.remove(file_path)
            print(f"Successfully reencoded audio and fixed: {file_name}")
        else:
            shutil.move(file_path, os.path.join(unrepaired_folder, file_name))
            print(f"Moved to unrepaired folder: {file_name}")

def main():
    json_file, dest_folder = get_user_input()
    file_list = load_json(json_file)
    process_files(file_list, dest_folder)

if __name__ == "__main__":
    main()
