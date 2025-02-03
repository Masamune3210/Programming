import os
import json
import shutil
import tkinter as tk
from tkinter import filedialog
from tqdm import tqdm  # Add tqdm for progress bar

# Minimum free space required beyond file size (in bytes)
EXTRA_SPACE_REQUIRED = 500 * 1024 * 1024  # 500MB
RETAG_THRESHOLD = 500 * 1024 * 1024  # 500MB
UPDATE_INTERVAL = 1  # Update JSON after every successful removal

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
        print(f"Error updating JSON file: {e}")

def copy_files(file_list_path, destination_folder):
    """Copy files from the JSON list to the destination folder while ensuring space and avoiding duplicates."""
    # Load JSON file
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

    # Sort files by size in ascending order
    files_to_copy.sort(key=lambda x: x['size'], reverse=False)

    # Update the JSON file with the sorted list of files
    data["files"] = files_to_copy
    save_json(file_list_path, data)

    # Calculate how many files can be copied based on available space
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

    # Check if there's enough space to copy any files
    if not eligible_files:
        print(f"Not enough space to copy any files. Free space: {free_space / (1024**3):.2f} GB")
        return

    # Display how many files can be copied
    print(f"Free space: {free_space / (1024**3):.2f} GB")
    print(f"Space required for {len(eligible_files)} files: {total_space_needed / (1024**3):.2f} GB")

    retag_folder = os.path.join(destination_folder, "retag")
    os.makedirs(retag_folder, exist_ok=True)  # Ensure retag folder exists

    twenty_folder = os.path.join(destination_folder, "2160") # Create 2160 folder
    os.makedirs(twenty_folder, exist_ok=True)  # Ensure 2160 folder exists

    processed_count = 0 # Track how many files have been processed
    remaining_files = list(files_to_copy)  # Copy full list initially

    # Create progress bar using tqdm
    with tqdm(total=len(eligible_files), desc="Copying files", unit="file") as pbar:
        for file_entry in eligible_files[:]:  # Iterate over a copy to modify safely
            file_path = file_entry["file"]
            file_name = os.path.basename(file_path)
            file_size = file_entry["size"]

            if not os.path.exists(file_path):
                print(f"\nSkipping (not found): {file_path}")
                continue  # Don't process, try next time

            if "2160" in file_name:  # If the file contains "2160" in its name move it to a separate 2160 folder
                dest_path = os.path.join(twenty_folder, file_name)
            else:  # Move other files based on their sizes into different folders
                dest_path = os.path.join(retag_folder if file_size < RETAG_THRESHOLD else destination_folder, file_name)

            if os.path.exists(dest_path):
                print(f"\nAlready exists (treating as copied): {file_name}")
                remaining_files.remove(file_entry)  # Treat as successfully processed and remove
                processed_count += 1
            else:
                try:
                    print(f"\nCopying: {file_name} → {dest_path}")
                    shutil.copy2(file_path, dest_path)  # Copy with metadata
                    remaining_files.remove(file_entry)  # Remove successfully processed file
                    processed_count += 1
                except Exception as e:
                    print(f"Error copying {file_name}: {e}")
                    continue  # Don't remove, try again later

            # Update the progress bar
            pbar.update(1)

            # Update JSON file every successful process
            if processed_count % UPDATE_INTERVAL == 0:
                data["files"] = remaining_files
                save_json(file_list_path, data)

def get_paths():
    root = tk.Tk()
    root.withdraw() # Hide the actual Tkinter window 

    # Directory selection
    initial_dir = os.path.expanduser('E:\\')  # Default to Downloads folder
    destination_folder = filedialog.askdirectory(initialdir=initial_dir, title='Select Destination Folder:')

    if not destination_folder: # If user cancelled, return default path
        print('User cancelled the selection dialog, using default directory instead.')
        destination_folder = initial_dir  # Use E:\ as default

    file_list = filedialog.askopenfilename(initialdir=os.path.expanduser('G:\\Users\\Johnny\\Downloads\\Programming'), title='Select file list:',
    filetypes=(('json files', '*.json'),)) # Let user select json file
    return (file_list, destination_folder)

if __name__ == "__main__":
    file_list, destination = get_paths()

    if not os.path.isdir(destination):
        print("Invalid destination folder.")
    else:
        copy_files(file_list, destination)
