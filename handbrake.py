import os
import subprocess

def encode_video(input_file, output_file):
    # Command to run HandBrakeCLI
    command = [
        "HandBrakeCLI", 
        "-i", input_file,         # Input file
        "-o", output_file,        # Output file
        "--preset", "Fast 1080p30" # Preset (can be modified)
    ]
    
    try:
        # Running the HandBrakeCLI command
        subprocess.run(command, check=True)
        print(f"Encoding complete: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error encoding video: {e}")

def process_folder(source_folder, destination_folder):
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
            
            # Call HandBrakeCLI to encode the video
            encode_video(file_path, output_file)

def main():
    # Ask the user for source and destination folders
    source_folder = input("Enter the source folder path: ")
    destination_folder = input("Enter the destination folder path: ")

    # Check if the source folder exists
    if not os.path.exists(source_folder):
        print("Source folder does not exist.")
        return

    # Process the files in the source folder
    process_folder(source_folder, destination_folder)

if __name__ == "__main__":
    main()
