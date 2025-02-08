import os
import subprocess
import glob
import sys

# The list containing the files to compress
files = []

# The folders where to look for files
wsl_folders = [
    os.path.join(os.getenv('LOCALAPPDATA', ''), 'Packages'),
    os.path.join(os.getenv('LOCALAPPDATA', ''), 'Docker'),
    r'D:\WSL2'
]

# Allow user definitions via an environment variable, WSL_FOLDERS
wsl_env_folders = os.getenv('WSL_FOLDERS')
if wsl_env_folders:
    for folder in wsl_env_folders.split(';'):
        print(f' - Additional user path: {folder}')
        wsl_folders.append(folder)

# Find the files in all the authorized folders
for wsl_folder in wsl_folders:
    if os.path.exists(wsl_folder):
        for root, _, _ in os.walk(wsl_folder):
            ext4_files = glob.glob(os.path.join(root, 'ext4.vhdx'))
            for file in ext4_files:
                print(f'- Found EXT4 disk: {file}')
                files.append(file)

if not files:
    raise RuntimeError("We could not find a file called ext4.vhdx in LOCALAPPDATA\\Packages or LOCALAPPDATA\\Docker or WSL_FOLDERS")

print(f' - Found {len(files)} VHDX file(s)')
print(' - Shutting down WSL2')

# Run WSL commands
try:
    subprocess.run(['wsl', '-e', 'sudo', 'fstrim', '/'], check=True)
    subprocess.run(['wsl', '--shutdown'], check=True)
except subprocess.CalledProcessError as e:
    print(f"Error running WSL commands: {e}")
    sys.exit(1)

# Compact the disks
for disk in files:
    print("-----")
    print(f"Disk to compact: {disk}")
    try:
        print(f"Length: {os.path.getsize(disk) / (1024 * 1024):.2f} MB")
    except OSError as e:
        print(f"Error getting size of {disk}: {e}")
        continue

    print("Compacting disk (starting diskpart)")
    
    diskpart_commands = f"""
    select vdisk file={disk}
    attach vdisk readonly
    compact vdisk
    detach vdisk
    exit
    """
    
    try:
        subprocess.run(['diskpart'], input=diskpart_commands, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error compacting disk {disk}: {e}")
        continue
    
    try:
        print(f"Success. Compacted {disk}.")
        print(f"New length: {os.path.getsize(disk) / (1024 * 1024):.2f} MB")
    except OSError as e:
        print(f"Error getting new size of {disk}: {e}")

print("=======")
print(f"Compacting of {len(files)} file(s) complete")
