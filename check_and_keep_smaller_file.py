import os
import shutil

def get_user_input(prompt):
    while True:
        path = input(prompt).strip()
        if os.path.isdir(path):
            return path
        else:
            print("Invalid directory. Please enter a valid path.")

def compare_and_keep_smaller(source_dir, dest_dir, retag_dir):
    for root, _, files in os.walk(source_dir):
        for file in files:
            source_path = os.path.join(root, file)
            dest_path = os.path.join(dest_dir, file)  # Destination is flat
            
            # Always keep files in 'retag' folders and delete destination copies
            if 'retag' in root.split(os.sep):
                if os.path.exists(dest_path):
                    print(f"Keeping source (retag folder): {source_path} and deleting destination: {dest_path}")
                    os.remove(dest_path)
                continue
            
            if os.path.exists(dest_path):
                source_size = os.path.getsize(source_path)
                dest_size = os.path.getsize(dest_path)
                
                if source_size < dest_size:
                    print(f"Keeping source: {source_path} (smaller than destination)")
                    os.remove(dest_path)
                elif source_size > dest_size:
                    print(f"Moving source to retag folder: {source_path} (larger than destination)")
                    try:
                        os.makedirs(retag_dir, exist_ok=True)
                        shutil.move(source_path, os.path.join(retag_dir, file))
                    except Exception as e:
                        print(f"Error moving source file {source_path} to retag folder: {e}")
                else:
                    print(f"Keeping source: {source_path} (same size as destination)")
                    os.remove(dest_path)

def main():
    source_dir = get_user_input("Enter the source directory: ")
    dest_dir = get_user_input("Enter the destination directory: ")
    retag_dir = get_user_input("Enter the retag directory: ")
    
    compare_and_keep_smaller(source_dir, dest_dir, retag_dir)
    print("Processing complete.")

if __name__ == "__main__":
    main()
