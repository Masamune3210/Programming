import os
import subprocess

def encode_video(input_file, output_file, preset_file):
    # Command to run HandBrakeCLI
    command = [
        "HandBrakeCLI", 
        "--preset-import-file", preset_file,  # Import the selected preset file
        "-i", input_file,                     # Input file
        "-o", output_file,                    # Output file
    ]
    
    try:
        # Running the HandBrakeCLI command
        subprocess.run(command, check=True)
        print(f"Encoding complete: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error encoding video: {e}")

def process_folder(source_folder, destination_folder, preset_file):
    # Ensure the destination folder exists
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # Loop through each file in the source folder
    for filename in os.listdir(source_folder):
        file_path = os.path.join(source_folder, filename)

        # Check if it's a video file (basic check for common extensions)
        if os.path.isfile(file_path) and filename.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
            # Prepare the output file path (same filename as input)
            output_file = os.path.join(destination_folder, filename)
            print(f"Processing: {filename}")
            
            # Call HandBrakeCLI to encode the video with the selected preset
            encode_video(file_path, output_file, preset_file)

def main():
    # Scan the script directory for all .json files
    script_directory = os.path.dirname(os.path.realpath(__file__))
    preset_files = [f for f in os.listdir(script_directory) if f.endswith('.json') and f != 'files_to_process.json']

    if not preset_files:
        print("No preset files found in the script directory.")
        return

    # Display preset options to the user
    print("Available presets:")
    for index, preset_file in enumerate(preset_files, 1):
        print(f"{index}: {preset_file}")

    # Prompt the user to select a preset
    preset_choice = input(f"Select a preset by number (1-{len(preset_files)}): ")
    
    # Check if the user input is valid
    if not preset_choice.isdigit() or int(preset_choice) < 1 or int(preset_choice) > len(preset_files):
        print("Invalid choice. Exiting.")
        return

    # Get the selected preset file
    preset_file = preset_files[int(preset_choice) - 1]
    preset_path = os.path.join(script_directory, preset_file)

    # Ask the user for source and destination folders
    source_folder = input("Enter the source folder path: ")
    destination_folder = input("Enter the destination folder path: ")

    # Check if the source folder exists
    if not os.path.exists(source_folder):
        print("Source folder does not exist.")
        return

    # Check if the preset file exists
    if not os.path.exists(preset_path):
        print(f"Preset file '{preset_file}' does not exist.")
        return

    # Process the files in the source folder
    process_folder(source_folder, destination_folder, preset_path)

if __name__ == "__main__":
    main()
