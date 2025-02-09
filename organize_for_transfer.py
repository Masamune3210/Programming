import os
import re
import shutil
import time

def is_file_locked(file_path):
    """Check if a file is locked by another process."""
    try:
        with open(file_path, 'a'):
            return False
    except IOError:
        return True

def is_file_being_written(file_path):
    """Check if a file is being written to by monitoring its size."""
    size1 = os.path.getsize(file_path)
    time.sleep(1)
    size2 = os.path.getsize(file_path)
    time.sleep(1)
    size3 = os.path.getsize(file_path)
    return size1 != size2 or size2 != size3

def organize_files(base_folder):
    if not os.path.isdir(base_folder):
        print("Invalid folder path. Please provide a valid directory.")
        return
    
    # Regex patterns to match the specified naming schemes
    single_episode_pattern = re.compile(r"^(.*?) - S(\d+)E(\d+) - .*?\.(\w+)$")
    multiple_episode_pattern = re.compile(r"^(.*?) - S(\d+)E(\d+(-E\d+)?) - .*?\.(\w+)$")
    
    files = [f for f in os.listdir(base_folder) if os.path.isfile(os.path.join(base_folder, f))]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(base_folder, x)), reverse=True)
    
    for i, file_name in enumerate(files):
        file_path = os.path.join(base_folder, file_name)
        
        if os.path.isfile(file_path):
            if i == 0 and (is_file_locked(file_path) or is_file_being_written(file_path)):
                print(f"Most recent file is currently locked or being written to and will be skipped: {file_name}")
                continue

            match = single_episode_pattern.match(file_name)
            if not match:
                match = multiple_episode_pattern.match(file_name)
            
            if match:
                show_name, season_num, episode_num, extension = match.groups()[:4]
                season_folder = f"Season {int(season_num)}"
                destination_folder = os.path.join(base_folder, show_name.strip(), season_folder)
                
                try:
                    os.makedirs(destination_folder, exist_ok=True)
                    destination_path = os.path.join(destination_folder, file_name)
                    shutil.move(file_path, destination_path)
                    print(f"Moved: {file_name} -> {destination_path}")
                except OSError as e:
                    print(f"Error moving file {file_name}: {e}")
                except Exception as e:
                    print(f"Unexpected error: {e}")
            else:
                print(f"File does not match pattern and will not be moved: {file_name}")
        else:
            print(f"Skipping non-file item: {file_name}")

if __name__ == "__main__":
    try:
        folder_path = input("Enter the folder path to organize: ").strip()
        organize_files(folder_path)
    except Exception as e:
        print(f"An error occurred: {e}")
