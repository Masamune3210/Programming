import os
import json
import shutil
import tkinter as tk
from tkinter import filedialog
from tqdm import tqdm  # Add tqdm for progress bar
import logging
import sys
import send2trash  # Add send2trash for sending files to recycle bin

# Configurable settings
LOG_FILE = 'process_errors.log'
EXTRA_SPACE_REQUIRED = 500 * 1024 * 1024  # 500MB
RETAG_THRESHOLD = 500 * 1024 * 1024  # 500MB
CHECK_FOLDER = 'Y:\\Media\\Plex Media\\Handbrake Output'
NON_ENGLISHJSON = 'non_english_audio.json'
DEFAULT_SOURCE_DIR = 'E:\\'
DEFAULT_JSON_DIR = 'G:\\Users\\Johnny\\Downloads\\Programming'
DEFAULT_JSON_FILE = 'files_to_process.json'

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def get_free_space(folder):
    """Return free space available on the drive containing the folder using shutil."""
    try:
        disk_usage = shutil.disk_usage(folder)
        return disk_usage.free  # Return the free space available
    except FileNotFoundError:
        logging.error(f"Folder not found: {folder}")
        return 0
    except PermissionError:
        logging.error(f"Permission denied: {folder}")
        return 0

def save_json(file_list_path, data):
    """Save the updated file list back to JSON to keep progress consistent."""
    try:
        with open(file_list_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except FileNotFoundError:
        logging.error(f"File not found: {file_list_path}")
    except PermissionError:
        logging.error(f"Permission denied: {file_list_path}")
    except Exception as e:
        logging.error(f"Error updating JSON file: {e}")

def delete_partial_file(file_path):
    """Send the file to the recycle bin if it exists and is not fully copied."""
    if os.path.exists(file_path):
        try:
            print(f"Sending partial file to recycle bin: {file_path}")
            send2trash.send2trash(file_path)
        except FileNotFoundError:
            logging.error(f"File not found: {file_path}")
        except PermissionError:
            logging.error(f"Permission denied: {file_path}")
        except Exception as e:
            logging.error(f"Error sending partial file {file_path} to recycle bin: {e}")

def copy_file_with_progress(src, dst):
    """Copy a file and show a progress bar for the current file copy."""
    try:
        total_size = os.path.getsize(src)
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Copying {os.path.basename(src)}") as pbar:
                while (chunk := fsrc.read(1024 * 1024)):  # 1MB chunks
                    fdst.write(chunk)
                    pbar.update(len(chunk))
    except FileNotFoundError:
        logging.error(f"File not found: {src} or {dst}")
    except PermissionError:
        logging.error(f"Permission denied: {src} or {dst}")
    except Exception as e:
        logging.error(f"Error copying file from {src} to {dst}: {e}")

def move_file_with_progress(src, dst):
    """Move a file and show a progress bar for the current file move."""
    try:
        total_size = os.path.getsize(src)
        with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=f"Moving {os.path.basename(src)}") as pbar:
                while (chunk := fsrc.read(1024 * 1024)):  # 1MB chunks
                    fdst.write(chunk)
                    pbar.update(len(chunk))
        os.remove(src)
    except FileNotFoundError:
        logging.error(f"File not found: {src} or {dst}")
    except PermissionError:
        logging.error(f"Permission denied: {src} or {dst}")
    except Exception as e:
        logging.error(f"Error moving file from {src} to {dst}: {e}")

def remove_existing_files(file_list_path, check_folder=CHECK_FOLDER):
    """Remove files from the JSON list if they already exist in the check_folder."""
    try:
        with open(file_list_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Error loading JSON file: {e}")
        return

    files_to_check = data.get("files", [])
    if not isinstance(files_to_check, list):
        logging.error("Invalid format: 'files' should be a list.")
        return

    updated_files = []
    for file_entry in files_to_check:
        file_name = os.path.basename(file_entry["file"])
        check_path = os.path.join(check_folder, file_name)
        if not os.path.exists(check_path):
            updated_files.append(file_entry)

    data["files"] = updated_files
    save_json(file_list_path, data)

def process_json(file_list_path, destination_folder):
    """Copy files from the JSON list to the destination folder while ensuring space and avoiding duplicates."""
    remove_existing_files(file_list_path)

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
    if free_space == 0:
        print("Unable to determine free space or insufficient permissions.")
        return

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

    # Check if the JSON file is named non_english_audio.json
    is_non_english_audio = os.path.basename(file_list_path) == NON_ENGLISHJSON

    if not is_non_english_audio:
        retag_folder = os.path.join(destination_folder, "retag")
        os.makedirs(retag_folder, exist_ok=True)
        twenty_folder = os.path.join(destination_folder, "2160")
        os.makedirs(twenty_folder, exist_ok=True)
        kids_folder = os.path.join(destination_folder, "kids")
        os.makedirs(kids_folder, exist_ok=True)

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

                if is_non_english_audio:
                    dest_path = os.path.join(destination_folder, file_name)
                else:
                    if "2160" in file_name:
                        dest_path = os.path.join(twenty_folder, file_name)
                    else:
                        dest_path = os.path.join(retag_folder if file_size < RETAG_THRESHOLD else destination_folder, file_name)

                # Check if the file already exists in the destination or kids folder
                kids_dest_path = os.path.join(kids_folder, file_name)
                if os.path.exists(dest_path) or os.path.exists(kids_dest_path):
                    print(f"\nAlready exists (treating as copied): {file_name}")
                    remaining_files.remove(file_entry)
                    processed_count += 1
                else:
                    try:
                        if is_non_english_audio:
                            print(f"\nMoving: {file_name} → {dest_path}")
                            current_file_path = dest_path  # Store the current destination path of the file being moved
                            move_file_with_progress(file_path, dest_path)  # Move the file with progress bar
                        else:
                            if file_name.lower().endswith('.mp4'):
                                print(f"\nCopying: {file_name} → {dest_path}")
                                current_file_path = dest_path  # Store the current destination path of the file being copied
                                copy_file_with_progress(file_path, dest_path)  # Copy the file with progress bar
                            else:
                                print(f"\nMoving: {file_name} → {dest_path}")
                                move_file_with_progress(file_path, dest_path)  # Move non-MP4 files directly

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
        # Clean up: delete the partially processed file if it was being processed
        if current_file_path and os.path.exists(current_file_path):
            print(f"Deleting partially processed file: {current_file_path}")
            os.remove(current_file_path)
        logging.shutdown()
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) == 0:
            os.remove(LOG_FILE)
            print("Deleted empty process_errors.log file")
        sys.exit(0)
    data["files"] = remaining_files
    save_json(file_list_path, data)
    print("File processing complete.")

def get_paths():
    root = tk.Tk()
    root.withdraw()
    initial_dir = os.path.expanduser(DEFAULT_SOURCE_DIR)
    destination_folder = filedialog.askdirectory(initialdir=initial_dir, title='Select Destination Folder:')

    if not destination_folder:
        print('User cancelled the selection dialog, using default directory instead.')
        destination_folder = initial_dir

    file_list = filedialog.askopenfilename(initialdir=os.path.expanduser(DEFAULT_JSON_DIR), title='Select File List:', filetypes=(('JSON Files', '*.json'),))

    if not file_list:
        print('User cancelled the file list selection, using default JSON file instead.')
        file_list = os.path.join(DEFAULT_JSON_DIR, DEFAULT_JSON_FILE)
    
    return file_list, destination_folder

if __name__ == "__main__":
    file_list, destination = get_paths()
    if not os.path.isdir(destination):
        print("Invalid destination folder.")
    else:
        process_json(file_list, destination)