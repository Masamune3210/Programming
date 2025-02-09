import os
import subprocess
import shutil
from tqdm import tqdm
import send2trash  # Add send2trash for sending files to recycle bin

# Configurable settings
TOOL_TEXT = "HandBrake 1.9.0 2024120100"  # Text to be written to the Tool tag
MP4TAG_PATH = r"C:\\Tools\\mp4tag\\mp4tag.exe"  # Path to the mp4tag executable
SUPPORTED_EXTENSIONS = ('.mkv', '.webm', '.avi', '.mpg')
FAILED_FOLDER_NAME = "failedconv"
TAGGED_FOLDER_NAME = "tagged"

def verify_file_with_ffprobe(file_path):
    """Verify the output file using ffprobe."""
    ffprobe_command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    ffprobe_result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return ffprobe_result.returncode == 0 and ffprobe_result.stdout.strip() != b''

def convert_and_tag_mp4(source_folder, destination_folder):
    # Ensure the source folder exists
    if not os.path.exists(source_folder):
        print(f"\nSource folder does not exist: {source_folder}")
        return

    # Ensure the destination folder exists or create it
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        print(f"\nDestination folder created: {destination_folder}")

    # Initialize lists to track unprocessed files
    unsupported_files = []
    failed_tagging_files = []
    failed_conversions = []

    # Create a folder for failed conversions
    failed_folder = os.path.join(source_folder, FAILED_FOLDER_NAME)
    os.makedirs(failed_folder, exist_ok=True)

    while True:
        # Get a list of all files in the source folder
        all_files = []
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                all_files.append(os.path.join(root, file))

        source_files = [file for file in all_files if file.lower().endswith(SUPPORTED_EXTENSIONS)]
        unsupported_files.extend([file for file in all_files if not file.lower().endswith(SUPPORTED_EXTENSIONS + ('.mp4',))])

        conversion_made = False
        for file in tqdm(source_files, desc="Converting Files", unit="file"):
            output_file_path = os.path.join(source_folder, os.path.basename(file).replace(os.path.splitext(file)[1], ".mp4"))

            if os.path.exists(output_file_path):
                print(f"\nSkipping existing file: {output_file_path}")
                continue

            ffmpeg_command = [
                "ffmpeg", "-fflags", "+genpts", "-i", file, "-c:v", "copy", "-c:a", "copy", "-map", "0:v", "-map", "0:a", output_file_path
            ]

            try:
                result = subprocess.run(ffmpeg_command, check=True, stderr=subprocess.PIPE)
                result.check_returncode()

                # Verify the output file using ffprobe
                if not verify_file_with_ffprobe(output_file_path):
                    print(f"\nError: Verification failed for '{output_file_path}'. Moving original file to 'failedconv'.")
                    failed_conversions.append(file)
                    send2trash.send2trash(output_file_path)  # Send failed conversion to recycle bin
                    shutil.move(file, os.path.join(failed_folder, os.path.basename(file)))  # Move source file
                    continue

                # If ffprobe is successful, send the original file to recycle bin
                send2trash.send2trash(file)
                print(f"\nConverted and sent original file to recycle bin: {file}")
                conversion_made = True
            except subprocess.CalledProcessError as e:
                error_message = e.stderr.decode()
                print(f"\nFailed to convert file: {file}. Error: {error_message}. Moving to 'failedconv'.")
                failed_conversions.append(file)
                shutil.move(file, os.path.join(failed_folder, os.path.basename(file)))
            except Exception as e:
                print(f"\nUnexpected error during conversion: {e}. Moving to 'failedconv'.")
                failed_conversions.append(file)
                shutil.move(file, os.path.join(failed_folder, os.path.basename(file)))

        # Restart the loop if any files were converted
        if conversion_made:
            print("\nRescanning the folder for newly converted files...")
            continue
        else:
            break

    # Tag all MP4 files (excluding failed conversions)
    all_mp4_files = [file for file in all_files if file.lower().endswith('.mp4')]
    for file in tqdm(all_mp4_files, desc="Tagging Files", unit="file"):
        output_file = os.path.join(destination_folder, os.path.basename(file))

        # Check if the tagged file already exists
        if os.path.exists(output_file):
            print(f"\nSkipping tagging, file already exists: {output_file}")
            send2trash.send2trash(file)  # Send original file to recycle bin
            continue

        escaped_tool_text = f'{TOOL_TEXT}'
        command = [MP4TAG_PATH, '--set', f'Tool:S:{escaped_tool_text}', file, output_file]

        print(f"\nTagging file: {file}")
        try:
            subprocess.run(command, check=True)
            print(f"\nSuccess: Tagged file saved to '{output_file}'.")
            send2trash.send2trash(file)  # Send original file to recycle bin after successful tagging
        except subprocess.CalledProcessError as e:
            print(f"\nError: Failed to write the Tool tag for '{file}'. Error: {e}")
            failed_tagging_files.append(file)
        except Exception as e:
            print(f"\nUnexpected error during tagging: {e}")
            failed_tagging_files.append(file)

    # Organize files into subfolders of 99 files each
    all_tagged_files = [file for file in os.listdir(destination_folder) if file.lower().endswith('.mp4')]
    if len(all_tagged_files) > 99:
        print("\nOrganizing files into folders of 99...")

        folder_index = 1
        current_folder = os.path.join(destination_folder, str(folder_index))
        os.makedirs(current_folder, exist_ok=True)

        file_count = 0
        for file in tqdm(all_tagged_files, desc="Moving Files", unit="file"):
            if file_count >= 99:
                folder_index += 1
                current_folder = os.path.join(destination_folder, str(folder_index))
                os.makedirs(current_folder, exist_ok=True)
                file_count = 0

            shutil.move(os.path.join(destination_folder, file), os.path.join(current_folder, file))
            print(f"\nMoved file: {file} to folder: {folder_index}")
            file_count += 1
    else:
        print("\nLess than 100 files; skipping folder organization.")

    # Print summary of unprocessed files
    if unsupported_files:
        print("\nThe following unsupported files were not processed:")
        for file in unsupported_files:
            print(file)

    if failed_conversions:
        print("\nThe following files failed conversion and were moved to 'failedconv':")
        for file in failed_conversions:
            print(file)

    if failed_tagging_files:
        print("\nThe following files failed tagging:")
        for file in failed_tagging_files:
            print(file)

    print("\nScript completed successfully.")


# Example usage
source_folder = input("Enter the source folder path: ")
destination_folder = input("Enter the destination folder path: ")
convert_and_tag_mp4(source_folder, destination_folder)