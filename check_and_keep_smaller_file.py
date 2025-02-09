import os
import shutil
import errno
import send2trash  # Add send2trash for sending files to recycle bin

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
            
            # Always keep files in 'retag' folders and send destination copies to recycle bin
            if 'retag' in root.split(os.sep):
                if os.path.exists(dest_path):
                    print(f"Sending destination file to recycle bin: {dest_path}")
                    send2trash.send2trash(dest_path)
                continue
            
            if os.path.exists(dest_path):
                try:
                    source_size = os.path.getsize(source_path)
                    dest_size = os.path.getsize(dest_path)
                    
                    # Print sizes of both files
                    print(f"Source file size: {source_size} bytes")
                    print(f"Destin file size: {dest_size} bytes")
                    
                    if source_size < dest_size:
                        print(f"Destination file is larger: {dest_path} (sending it to recycle bin and moving source to retag folder)")
                        shutil.move(source_path, os.path.join(retag_dir, file))
                        send2trash.send2trash(dest_path)  # Send the larger destination file to recycle bin
                    elif source_size > dest_size:
                        print(f"Source file is larger: {source_path} (sending the source file to recycle bin and leaving destination file)")
                        send2trash.send2trash(source_path)  # Send the larger source file to recycle bin
                    else:
                        print(f"Source and destination files are of the same size: {source_path} (moving source to retag folder)")
                        shutil.move(source_path, os.path.join(retag_dir, file))
                        send2trash.send2trash(dest_path)  # Send the destination file to recycle bin
                
                except OSError as e:
                    # Check for file lock (error code 13 is a common lock error)
                    if e.errno == errno.EACCES or e.errno == errno.EBUSY:
                        print(f"File is locked, skipping: {source_path}")
                    else:
                        # Any other OSError should be raised again
                        raise e

def main():
    source_dir = get_user_input("Enter the source directory: ")
    dest_dir = get_user_input("Enter the destination directory: ")
    
    compare_and_keep_smaller(source_dir, dest_dir)
    print("Processing complete.")

if __name__ == "__main__":
    main()
