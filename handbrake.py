import os
import subprocess
import shutil
import sys

def find_handbrakecli():
    handbrakecli_path = r"C:\Tools\handbrakecli"
    if not os.path.exists(handbrakecli_path):
        handbrakecli_path = input("HandBrakeCLI not found at default location. Please provide the full path to HandBrakeCLI: ")
        if not os.path.exists(handbrakecli_path):
            print("HandBrakeCLI not found at the provided path. Exiting.")
            sys.exit(1)
    return handbrakecli_path

def encode_video(input_file, output_file, preset_file, handbrakecli_path):
    # Command to run HandBrakeCLI
    command = [
        os.path.join(handbrakecli_path, "HandBrakeCLI.exe"),  # Path to HandBrakeCLI executable
        "--preset-import-file", preset_file,  # Import the selected preset file
        "-i", input_file,                     # Input file
        "-o", output_file,                    # Output file
    ]
    try:
        # Running the HandBrakeCLI command
        subprocess.run(command, check=True)
        print(f"Encoding complete: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error encoding video {input_file}: {e}")
        return False
    return True

def handle_file(input_file, output_file, source_folder):
    # Get sizes of both files
    input_size = os.path.getsize(input_file)
    output_size = os.path.getsize(output_file)

    # Check if the output file is smaller than the input file
    if output_size < input_size:
        # If the output is smaller, delete the input file
        os.remove(input_file)
        print(f"Input file {input_file} was larger, deleted.")
    else:
        # If the output is not smaller, delete the output and move input to retag folder
        os.remove(output_file)
        retag_folder = os.path.join(source_folder, "retag")
        if not os.path.exists(retag_folder):
            os.makedirs(retag_folder)
        # Move the original file to the 'retag' folder
        shutil.move(input_file, os.path.join(retag_folder, os.path.basename(input_file)))
        print(f"Output file is not smaller. Moved input file to 'retag' folder.")

def handle_encoding_error(input_file, source_folder):
    # Create the 'errored' folder if it doesn't exist
    errored_folder = os.path.join(source_folder, "errored")
    if not os.path.exists(errored_folder):
        os.makedirs(errored_folder)

    # Move the source file to the 'errored' folder
    shutil.move(input_file, os.path.join(errored_folder, os.path.basename(input_file)))
    print(f"Encoding error occurred. Moved {input_file} to 'errored' folder.")

def get_preset_for_file(file_path, source_folder):
    # Determine the preset based on the directory structure
    relative_path = os.path.relpath(file_path, source_folder)
    folder_name = os.path.dirname(relative_path)

    if folder_name.lower() == "kids":
        return "kids.json"
    elif folder_name.lower() == "2160":
        return "4k.json"
    else:
        return "1080.json"

def process_folder(source_folder, destination_folder, preset_files, handbrakecli_path):
    # Ensure the destination folder exists
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # Walk through the source folder recursively
    for root, dirs, files in os.walk(source_folder):
        # Skip the 'more' folder
        if 'more' in dirs:
            dirs.remove('more')
        if 'retag' in dirs:
            dirs.remove('retag')

        for filename in files:
            file_path = os.path.join(root, filename)

            # Check if it's a video file (basic check for common extensions)
            if filename.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                # Determine which preset to use based on folder name
                preset_file = get_preset_for_file(file_path, source_folder)
                
                # Verify if the preset file exists
                if preset_file not in preset_files:
                    print(f"Preset file '{preset_file}' not found. Exiting.")
                    sys.exit(1)  # Halt the script if the preset file is not found
                
                preset_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), preset_file)
                if not os.path.exists(preset_path):
                    print(f"Preset file '{preset_file}' does not exist. Exiting.")
                    sys.exit(1)  # Halt the script if the preset file doesn't exist

                # Prepare the output file path (same filename as input, but in destination folder)
                output_file = os.path.join(destination_folder, filename)
                print(f"Processing: {filename}")

                # Call HandBrakeCLI to encode the video with the selected preset
                if encode_video(file_path, output_file, preset_path, handbrakecli_path):
                    # After encoding, check file sizes and handle accordingly
                    handle_file(file_path, output_file, source_folder)
                else:
                    # If encoding fails, handle the error by moving the file to 'errored'
                    handle_encoding_error(file_path, source_folder)

def main():
    # Scan the script directory for all .json files, excluding 'files_to_process.json'
    script_directory = os.path.dirname(os.path.realpath(__file__))
    preset_files = [f for f in os.listdir(script_directory) if f.endswith('.json') and f != 'files_to_process.json']

    if not preset_files:
        print("No preset files found in the script directory. Exiting.")
        sys.exit(1)  # Halt the script if no preset files are found

    # Ask the user for source and destination folders
    source_folder = input("Enter the source folder path: ")
    destination_folder = input("Enter the destination folder path: ")

    # Check if the source folder exists
    if not os.path.exists(source_folder):
        print("Source folder does not exist. Exiting.")
        sys.exit(1)  # Halt the script if the source folder does not exist

    # Find HandBrakeCLI path
    handbrakecli_path = find_handbrakecli()

    # Process the files in the source folder
    process_folder(source_folder, destination_folder, preset_files, handbrakecli_path)

if __name__ == "__main__":
    main()
