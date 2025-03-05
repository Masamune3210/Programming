import os
import re
import requests
import webbrowser
from datetime import datetime

gog_api_url = "https://gog-games.to/api/web/query-game/"
gog_game_url = "https://gog-games.to/game/"

def extract_game_info(filename):
    match = re.search(r"setup_(.+?)_([\d\.r]+)(?:_|\s)\((\d+)\)", filename)
    if match:
        title = match.group(1).replace("_", " ").title()
        version = match.group(2)
        game_id = match.group(3)
        print(f"Extracted: Title={title}, Version={version}, ID={game_id}")  # Debug print
        return title, version, game_id
    print(f"Failed to extract info from: {filename}")  # Debug print
    return None, None, None

def get_latest_version(game_id):
    response = requests.get(f"{gog_api_url}{game_id}")
    print(f"API Request: {gog_api_url}{game_id} -> Status: {response.status_code}")  # Debug print
    if response.status_code == 200:
        print(f"API Response: {response.text[:200]}...")  # Debug print (truncated for readability)
        game_info = response.json().get('game_info', {})
        files = response.json().get('files', [])
        if game_info:
            last_update = game_info.get('last_update')
            latest_version = None
            for file in files:
                match = re.search(r"_([\d\.r]+)_\(\d+\)\.exe", file['name'])
                if match:
                    latest_version = match.group(1)
                    break
            if latest_version and re.match(r"^\d+(\.\d+)*$", latest_version):
                return latest_version, game_info.get('slug')
            elif last_update:
                return last_update, game_info.get('slug')
            else:
                print(f"No updates found for game ID {game_id}.")  # Debug print
                return "No updates", game_info.get('slug')
    return None, None

def scan_directory(directory):
    outdated_games = []
    detected_games = []
    checked_ids = set()
    for game_folder in os.scandir(directory):
        if game_folder.is_dir():
            if "[FitGirl Repack]" in game_folder.name or "[DODI Repack]" in game_folder.name:
                print(f"Skipping folder: {game_folder.name}")  # Debug print
                continue
            print(f"Checking game folder: {game_folder.name}")  # Debug print
            for entry in os.scandir(game_folder.path):
                print(f"Checking entry: {entry.name}")  # Debug print
                if entry.is_file():
                    if entry.name.startswith("setup_") and entry.name.endswith(".exe"):
                        print(f"File fits criteria: {entry.name}")  # Debug print
                        game_title, local_version, game_id = extract_game_info(entry.name)
                        if game_id and game_id not in checked_ids:
                            checked_ids.add(game_id)
                            if game_title and local_version:
                                latest_version, slug = get_latest_version(game_id)
                                detected_games.append((game_title, local_version, latest_version))
                                print(f"Detected: {game_title} (Local: {local_version}, Remote: {latest_version if latest_version else 'Unknown'})")
                                if latest_version and latest_version != local_version:
                                    outdated_games.append((game_title, local_version, latest_version, slug))
                                else:
                                    print(f"{game_title} is up to date.")
                    else:
                        print(f"File does not fit criteria: {entry.name}")  # Debug print
    print("\nDetected Games:")
    for title, local, latest in detected_games:
        print(f"{title} (Local: {local}, Remote: {latest if latest else 'Unknown'})")
    return outdated_games

def main():
    directory = input("Enter the path to your GOG installers folder: ").strip()
    if not os.path.isdir(directory):
        print("Invalid directory. Please enter a valid folder path.")
        return
    
    outdated_games = scan_directory(directory)
    
    if outdated_games:
        print("\nOutdated Games Found:")
        for i, (title, local, latest, slug) in enumerate(outdated_games, start=1):
            print(f"{i}. {title} (Local: {local} -> Latest: {latest})")
        
        open_pages = input("\nWould you like to open the pages for these games? (y/n): ").strip().lower()
        if open_pages == 'y':
            for _, _, _, slug in outdated_games:
                webbrowser.open(f"{gog_game_url}{slug}")
    else:
        print("\nAll games are up to date!")

if __name__ == "__main__":
    main()
