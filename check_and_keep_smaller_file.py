import os
import shutil

def get_user_input(prompt):
    while True:
        path = input(prompt).strip()
        if os.path.isdir(path):
            return path
        else:
            print("Invalid directory. Please enter a valid path.")

def compare_and_keep_smaller(source_dir, dest_dir):
    retag_dir = os.path.join(source_dir, "retag")
    os.makedirs(retag_dir, exist_ok=True)
    
    for root, _, files in os.walk(source_dir):
        for file in files:
            source_path = os.path.join(root, file)
            dest_path = os.path.join(dest_dir, file)  # Destination is flat
            
            # Always keep files in 'retag' folders and delete destination copies
            if 'retag' in root.split(os.sep):
                if os.path.exists(dest_path):
                    print(f"Deleting destination file: {dest_path}")
                    os.remove(dest_path)
                continue
            
            if os.path.exists(dest_path):
                source_size = os.path.getsize(source_path)
                dest_size = os.path.getsize(dest_path)
                
                if source_size < dest_size:
                    print(f"Destination file is larger: {dest_path} (deleting it and moving source to retag folder)")
                    shutil.move(source_path, os.path.join(retag_dir, file))  # Move the source file to retag
                    os.remove(dest_path)  # Remove the larger destination file
                elif source_size > dest_size:
                    print(f"Source file is larger: {source_path} (deleting the source file and leaving destination file)")
                    os.remove(source_path)  # Remove the larger source file
                else:
                    print(f"Source and destination files are of the same size: {source_path} (moving source to retag folder)")
                    shutil.move(source_path, os.path.join(retag_dir, file))  # Move the source file to retag folder
                    os.remove(dest_path)  # Remove the destination file

def main():
    source_dir = get_user_input("Enter the source directory: ")
    dest_dir = get_user_input("Enter the destination directory: ")
    
    compare_and_keep_smaller(source_dir, dest_dir)
    print("Processing complete.")

if __name__ == "__main__":
    main()
