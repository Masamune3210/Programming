import json
import os
import subprocess
import shutil
from tkinter import Tk, filedialog

# Configurable settings
REMUX_COMMAND = ['ffmpeg', '-i', '{input}', '-c', 'copy', '{output}']
REENCODE_COMMAND = ['ffmpeg', '-i', '{input}', '-c:v', 'copy', '-c:a', 'aac', '{output}']
CHECK_COMMAND = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', '{input}']

def get_user_input():
    root = Tk()
    root.withdraw()  # Hide the root window
    json_file = filedialog.askopenfilename(
        title="Select JSON File", 
        filetypes=[("JSON files", "*.json")], 
        initialdir="G:/Users/Johnny/Downloads/Programming"
    )
    os.makedirs('E:/fixing', exist_ok=True)
    dest_folder = filedialog.askdirectory(
        title="Select Destination Folder", 
        initialdir="E:/fixing"
    )
    return json_file, dest_folder

def load_json(json_file):
    try:
        with open(json_file, 'r') as file:
            data = json.load(file)
        return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading JSON file: {e}")
        return []

def remux_file(file_path, output_path):
    command = [arg.format(input=file_path, output=output_path) for arg in REMUX_COMMAND]
    try:
        result = subprocess.run(command, capture_output=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error remuxing file {file_path}: {e}")
        return False

def reencode_audio(file_path, output_path):
    command = [arg.format(input=file_path, output=output_path) for arg in REENCODE_COMMAND]
    try:
        result = subprocess.run(command, capture_output=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error reencoding audio for file {file_path}: {e}")
        return False

def check_file(file_path):
    command = [arg.format(input=file_path) for arg in CHECK_COMMAND]
    try:
        result = subprocess.run(command, capture_output=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error checking file {file_path}: {e}")
        return False

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

        try:
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
        except Exception as e:
            print(f"Unexpected error processing file {file_path}: {e}")
            shutil.move(file_path, os.path.join(unrepaired_folder, file_name))

def main():
    json_file, dest_folder = get_user_input()
    file_list = load_json(json_file)
    if not file_list:
        print("No files to process.")
        return
    process_files(file_list, dest_folder)

if __name__ == "__main__":
    main()
