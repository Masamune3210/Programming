import os
import re
import requests
import webbrowser
from datetime import datetime

GOG_API_URL = "https://gog-games.to/api/web/query-game/"
GOG_GAME_URL = "https://gog-games.to/game/"

def extract_game_info(filename):
    """Extract game title and ID from the filename."""
    match = re.search(r"setup_(.+?)_([\d\.r]+)(?:_|\s)\((\d+)\)", filename)
    if match:
        title = match.group(1).replace("_", " ").title()
        game_id = match.group(3)
        return title, game_id
    return None, None

def get_latest_update(game_title):
    """Fetch the latest update information for the game from the API."""
    formatted_title = game_title.replace(" ", "_")
    response = requests.get(f"{GOG_API_URL}{formatted_title}")
    
    if response.status_code == 200:
        game_info = response.json().get('game_info', {})
        if game_title.lower() in game_info.get('title', '').lower():
            last_update = game_info.get('last_update')
            if last_update:
                # Clean the returned date (remove time part)
                return last_update.split("T")[0], formatted_title
    return None, None

def scan_directory(directory):
    """Scan the directory for game installers and compare local dates with the latest updates."""
    outdated_games = []
    detected_games = set()  # Using a set to avoid duplicates
    queried_game_ids = set()  # Track which game IDs have already been queried
    
    for game_folder in os.scandir(directory):
        if game_folder.is_dir() and not any(repack in game_folder.name for repack in ["[FitGirl Repack]", "[DODI Repack]"]):
            for entry in os.scandir(game_folder.path):
                if entry.is_file() and entry.name.startswith("setup_") and entry.name.endswith(".exe"):
                    game_title, game_id = extract_game_info(entry.name)
                    if game_title:
                        # Add only unique game IDs to detected_games set
                        detected_games.add((game_title, game_id))
                        
                        # Query API only once per game ID
                        if game_id not in queried_game_ids:
                            queried_game_ids.add(game_id)
                            latest_update, formatted_title = get_latest_update(game_title)
                            if latest_update:
                                local_date = datetime.fromtimestamp(entry.stat().st_mtime).strftime('%Y-%m-%d')
                                if latest_update != local_date:
                                    outdated_games.append((game_title, local_date, latest_update, formatted_title))
    
    return outdated_games, list(detected_games)

def main():
    """Main function to handle user interaction and processing."""
    directory = input("Enter the path to your GOG installers folder: ").strip()
    if not os.path.isdir(directory):
        print("Invalid directory. Please enter a valid folder path.")
        return
    
    outdated_games, detected_games = scan_directory(directory)
    
    if detected_games:
        # Alphabetize the detected games by title
        detected_games.sort(key=lambda x: x[0].lower())
        
        print("\nDetected Games:")
        for title, game_id in detected_games:
            print(f"{title} (ID: {game_id})")
    
    if outdated_games:
        print("\nOutdated Games Found:")
        for i, (title, local_date, latest, _) in enumerate(outdated_games, start=1):
            print(f"{i}. {title} (Local Date: {local_date} -> Latest: {latest})")
        
        open_pages = input("\nWould you like to open the pages for these games? (y/n): ").strip().lower()
        if open_pages == 'y':
            for _, _, _, formatted_title in outdated_games:
                webbrowser.open(f"{GOG_GAME_URL}{formatted_title}")
    else:
        print("\nAll games are up to date!")

if __name__ == "__main__":
    main()
