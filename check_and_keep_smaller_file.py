import os

def get_user_input(prompt):
    while True:
        path = input(prompt).strip()
        if os.path.isdir(path):
            return path
        else:
            print("Invalid directory. Please enter a valid path.")

def compare_and_keep_smaller(source_dir, dest_dir):
    for root, _, files in os.walk(source_dir):
        for file in files:
            source_path = os.path.join(root, file)
            dest_path = os.path.join(dest_dir, os.path.relpath(source_path, source_dir))
            
            if os.path.exists(dest_path):
                source_size = os.path.getsize(source_path)
                dest_size = os.path.getsize(dest_path)
                
                if source_size < dest_size:
                    print(f"Keeping source: {source_path} (smaller than destination)")
                    os.remove(dest_path)
                elif source_size > dest_size:
                    print(f"Keeping destination: {dest_path} (smaller than source)")
                    os.remove(source_path)
                else:
                    print(f"Keeping source: {source_path} (same size as destination)")
                    os.remove(dest_path)

def main():
    source_dir = get_user_input("Enter the source directory: ")
    dest_dir = get_user_input("Enter the destination directory: ")
    
    compare_and_keep_smaller(source_dir, dest_dir)
    print("Processing complete.")

if __name__ == "__main__":
    main()
