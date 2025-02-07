import os
import json
import shutil
import tkinter as tk
from tkinter import filedialog
from tqdm import tqdm  # Add tqdm for progress bar
import logging
import sys

# Setup logging
logging.basicConfig(filename='copy_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Minimum free space required beyond file size (in bytes)
EXTRA_SPACE_REQUIRED = 500 * 1024 * 1024  # 500MB
RETAG_THRESHOLD = 500 * 1024 * 1024  # 500MB


def get_free_space(folder):
    """Return free space available on the drive containing the folder using shutil."""
    disk_usage = shutil.disk_usage(folder)
    return disk_usage.free  # Return the free space available

def save_json(file_list_path, data):
    """Save the updated file list back to JSON to keep progress consistent."""
    try:
        with open(file_list_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"Error updating JSON file: {e}")

def delete_partial_file(file_path):
    """Delete the file if it exists and is not fully copied."""
    if os.path.exists(file_path):
        try:
            print(f"Deleting partial file: {file_path}")
            os.remove(file_path)
        except Exception as e:
            logging.error(f"Error deleting partial file {file_path}: {e}")

def copy_file_with_progress(src, dst):
    """Copy a file and show a progress bar for the current file copy."""
    total_size = os.path.getsize(src)
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Copying {os.path.basename(src)}") as pbar:
            while (chunk := fsrc.read(1024 * 1024)):  # 1MB chunks
                fdst.write(chunk)
                pbar.update(len(chunk))

def move_file(src, dst):
    """Move a file directly from source to destination."""
    try:
        shutil.move(src, dst)
        print(f"Moved: {os.path.basename(src)} → {os.path.basename(dst)}")
    except Exception as e:
        logging.error(f"Error moving {os.path.basename(src)}: {e}")

def copy_files(file_list_path, destination_folder):
    """Copy files from the JSON list to the destination folder while ensuring space and avoiding duplicates."""
    try:
        with open(file_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Error loading JSON file: {e}")
        return

    files_to_copy = data.get("files", [])
    
    if not isinstance(files_to_copy, list):
        logging.error("Invalid format: 'files' should be a list.")
        return

    if not files_to_copy:
        print("No files to process.")
        return

    files_to_copy = [f for f in files_to_copy if "file" in f and "size" in f]
    files_to_copy.sort(key=lambda x: x['size'], reverse=False)

    free_space = get_free_space(destination_folder)
    total_space_needed = 0
    eligible_files = []
    for file_entry in files_to_copy:
        file_size = file_entry['size']
        if total_space_needed + file_size + EXTRA_SPACE_REQUIRED <= free_space:
            eligible_files.append(file_entry)
            total_space_needed += file_size
        else:
            break

    if not eligible_files:
        print(f"Not enough space to copy any files. Free space: {free_space / (1024**3):.2f} GB")
        return

    print(f"Free space: {free_space / (1024**3):.2f} GB")
    print(f"Space required for {len(eligible_files)} files: {total_space_needed / (1024**3):.2f} GB")

    retag_folder = os.path.join(destination_folder, "retag")
    os.makedirs(retag_folder, exist_ok=True)

    twenty_folder = os.path.join(destination_folder, "2160")
    os.makedirs(twenty_folder, exist_ok=True)

    processed_count = 0
    remaining_files = list(files_to_copy)

    current_file_path = None  # To store the current file being processed
    current_file_entry = None  # To store the current file entry in the list

    try:
        with tqdm(total=len(eligible_files), desc="Processing files", unit="file") as pbar:
            for file_entry in eligible_files[:]:
                file_path = file_entry["file"]
                file_name = os.path.basename(file_path)
                file_size = file_entry["size"]

                if not os.path.exists(file_path):
                    print(f"\nSkipping (not found): {file_path}")
                    remaining_files.remove(file_entry)  # Remove from processing list
                    data["files"] = remaining_files  # Update JSON data
                    save_json(file_list_path, data)  # Save changes immediately
                    continue

                if "2160" in file_name:
                    dest_path = os.path.join(twenty_folder, file_name)
                else:
                    dest_path = os.path.join(retag_folder if file_size < RETAG_THRESHOLD else destination_folder, file_name)

                if os.path.exists(dest_path):
                    print(f"\nAlready exists (treating as copied): {file_name}")
                    remaining_files.remove(file_entry)
                    processed_count += 1
                else:
                    try:
                        if file_name.lower().endswith('.mp4'):
                            print(f"\nCopying: {file_name} → {dest_path}")
                            current_file_path = dest_path  # Store the current destination path of the file being copied
                            copy_file_with_progress(file_path, dest_path)  # Copy the file with progress bar
                        else:
                            print(f"\nMoving: {file_name} → {dest_path}")
                            move_file(file_path, dest_path)  # Move non-MP4 files directly

                        # If copy or move was successful, remove the file from the remaining list
                        remaining_files.remove(file_entry)
                        processed_count += 1

                    except Exception as e:
                        logging.error(f"Error processing {file_name}: {e}")
                        delete_partial_file(current_file_path)  # Delete the partial file at the current destination
                        continue

                pbar.update(1)
                data["files"] = remaining_files
                save_json(file_list_path, data)
    except KeyboardInterrupt:
        print("\nProcess interrupted. Saving progress...")

        # Clean up: delete the partially copied file if it was being copied
        if current_file_path and os.path.exists(current_file_path):
            print(f"Deleting partially copied file: {current_file_path}")
            os.remove(current_file_path)
            logging.shutdown()
            if os.path.exists('copy_errors.log') and os.path.getsize('copy_errors.log') == 0:
                os.remove('copy_errors.log')
                print("Deleted empty copy_errors.log file")
                sys.exit(0)

    data["files"] = remaining_files
    save_json(file_list_path, data)
    print("File processing complete.")

    # Flush and close the log file before checking if it's empty
    logging.shutdown()
    # Check if the log file is empty and delete it if it is
    if os.path.exists('copy_errors.log') and os.path.getsize('copy_errors.log') == 0:
        os.remove('copy_errors.log')
        print("Deleted empty copy_errors.log file.")

def get_paths():
    root = tk.Tk()
    root.withdraw()
    initial_dir = os.path.expanduser('E:\\')
    destination_folder = filedialog.askdirectory(initialdir=initial_dir, title='Select Destination Folder:')

    if not destination_folder:
        print('User cancelled the selection dialog, using default directory instead.')
        destination_folder = initial_dir

    file_list = filedialog.askopenfilename(initialdir=os.path.expanduser('G:\\Users\\Johnny\\Downloads\\Programming'), title='Select File List:', filetypes=(('JSON Files', '*.json'),))

    if not file_list:
        print('User cancelled the file list selection.')
    
    return file_list, destination_folder

if __name__ == "__main__":
    file_list, destination = get_paths()

    if not os.path.isdir(destination):
        print("Invalid destination folder.")
    else:
        copy_files(file_list, destination)
