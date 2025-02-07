import os
import re
import shutil

def organize_files(base_folder):
    if not os.path.isdir(base_folder):
        print("Invalid folder path. Please provide a valid directory.")
        return
    
    # Regex pattern to match the specified naming scheme
    pattern = re.compile(r"^(.*?) - S(\d+)E(\d+) - .*?\.(\w+)$")
    
    for file_name in os.listdir(base_folder):
        file_path = os.path.join(base_folder, file_name)
        
        if os.path.isfile(file_path):
            match = pattern.match(file_name)
            if match:
                show_name, season_num, episode_num, extension = match.groups()
                season_folder = f"Season {int(season_num)}"
                destination_folder = os.path.join(base_folder, show_name.strip(), season_folder)
                
                os.makedirs(destination_folder, exist_ok=True)
                destination_path = os.path.join(destination_folder, file_name)
                
                shutil.move(file_path, destination_path)
                print(f"Moved: {file_name} -> {destination_path}")

if __name__ == "__main__":
    folder_path = input("Enter the folder path to organize: ").strip()
    organize_files(folder_path)
