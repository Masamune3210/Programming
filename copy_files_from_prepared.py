import os
import json
import shutil
import tkinter as tk
from tkinter import filedialog

# Minimum free space required beyond file size (in bytes)
EXTRA_SPACE_REQUIRED = 500 * 1024 * 1024  # 500MB
RETAG_THRESHOLD = 500 * 1024 * 1024  # 500MB
UPDATE_INTERVAL = 10  # Update JSON file every 10 successful removals

def get_free_space(folder):
    """Return free space available on the drive containing the folder using shutil."""
    disk_usage = shutil.disk_usage(folder)
    return disk_usage.free  # Return the free space available

def save_json(file_list_path, data):
    """Save the updated file list back to JSON to keep progress consistent."""
    try:
        with open(file_list_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print("JSON file updated.")
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

    retag_folder = os.path.join(destination_folder, "retag")
    os.makedirs(retag_folder, exist_ok=True)  # Ensure retag folder exists

    twenty_folder = os.path.join(destination_folder, "2160") # Create 2160 folder
    os.makedirs(twenty_folder, exist_ok=True)  # Ensure 2160 folder exists

    processed_count = 0 # Track how many files have been processed
    remaining_files = list(files_to_copy)  # Start with the full file list

    for file_entry in files_to_copy[:]:  # Iterate over a copy to modify safely
        file_path = file_entry["file"]
        file_name = os.path.basename(file_path)
        file_size = file_entry["size"]

        if not os.path.exists(file_path):
            print(f"Skipping (not found): {file_path}")
            continue  # Don't process, try next time

        if "2160" in file_name: # If the file contains "2160" in its name move it to a separate 2160 folder
            dest_path = os.path.join(twenty_folder, file_name)
        else: # Move other files based on their sizes into different folders
            dest_path = os.path.join(retag_folder if file_size < RETAG_THRESHOLD else destination_folder, file_name)

        if os.path.exists(dest_path):
            print(f"Already exists (treating as copied): {file_name}")
            remaining_files.remove(file_entry)  # Treat as successfully processed and remove
            processed_count += 1
        else:
            free_space = get_free_space(destination_folder)

            if free_space < (file_size + EXTRA_SPACE_REQUIRED):
                print(f"Skipping (not enough space): {file_name}")
                continue  # Don't process, try next time

            try:
                print(f"Copying: {file_name} → {dest_path}")
                shutil.copy2(file_path, dest_path)  # Copy with metadata
                remaining_files.remove(file_entry)  # Remove successfully processed file
                processed_count += 1
            except Exception as e:
                print(f"Error copying {file_name}: {e}")
                continue  # Don't remove, try again later

        # Update JSON file every 10 successful processes
        if processed_count % UPDATE_INTERVAL == 0:
            data["files"] = remaining_files
            save_json(file_list_path, data)

    # Final update to JSON file after loop
    data["files"] = remaining_files
    save_json(file_list_path, data)

    print("File processing complete.")

def get_paths():
    root = tk.Tk()
    root.withdraw() # Hide the actual Tkinter window 

    # Directory selection
    initial_dir = os.path.expanduser('E:\\')  # Default to Downloads folder
    destination_folder = filedialog.askdirectory(initialdir=initial_dir, title='Select Destination Folder:')

    if not destination_folder: # If user cancelled, return default path
        print ('User cancelled the selection dialog, using default directory instead.') 
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