import os
import re
import json
import webbrowser
import time
from datetime import datetime

GOG_API_URL = "https://gog-games.to/api/web/query-game/"
GOG_GAME_URL = "https://gog-games.to/game/"
DATABASE_FILE = "gog_games_database.json"

def load_game_database():
    """Load GOG games database from JSON file."""
    if os.path.isfile(DATABASE_FILE):
        with open(DATABASE_FILE, 'r', encoding='utf-8') as db_file:
            return json.load(db_file)
    return []

game_database = load_game_database()

def find_game_in_database_by_slug(slug):
    """Find game information in the local database by slug."""
    normalized_slug = slug.strip().lower()
    for game in game_database:
        db_slug = game["slug"].strip().lower()
        if db_slug == normalized_slug:
            return game["title"], game["id"], game["slug"], game.get("last_update")
    return slug, None, None, None

def extract_game_info_from_name_file(game_folder_path):
    """Check for a .name file in the game folder and return the proper title from the database."""
    for entry in os.scandir(game_folder_path):
        if entry.is_file() and entry.name.endswith(".name"):
            with open(entry.path, 'r', encoding='utf-8') as name_file:
                raw_slug = name_file.read().strip()
                return find_game_in_database_by_slug(raw_slug)
    return None, None, None, None

def extract_game_info(filename):
    """Extract game title and ID from the filename."""
    match = re.search(r"setup_(.+?)_([\d\.r]+)(?:_|\s)\((\d+)\)", filename)
    if match:
        title = match.group(1).replace("_", " ").title()
        return find_game_in_database_by_slug(title)
    return None, None, None, None

def generate_name_files(output_directory):
    """Generate .name files for all slugs found in the database."""
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    for game in game_database:
        slug = game["slug"]
        name_file_path = os.path.join(output_directory, f"{slug}.name")
        with open(name_file_path, "w", encoding="utf-8") as name_file:
            name_file.write(slug)
    
    print(f"Generated .name files in {output_directory}")

def scan_directory(directory):
    """Scan the directory for game installers and compare local dates with the latest updates."""
    outdated_games = []
    detected_games = set()
    
    for game_folder in os.scandir(directory):
        if game_folder.is_dir():
            if "[FitGirl Repacks]" in game_folder.name or "[DODI Repacks]" in game_folder.name:
                print(f"Skipping folder: {game_folder.name}")  # Debug print
                continue
            
            game_title, game_id, game_slug, last_update = extract_game_info_from_name_file(game_folder.path)
            local_timestamp = None
            
            if not game_title:
                for entry in os.scandir(game_folder.path):
                    if entry.is_file() and not entry.name.endswith(".name"):
                        game_title, game_id, game_slug, last_update = extract_game_info(entry.name)
                        local_timestamp = entry.stat().st_mtime  # Use file's modification date
                        break
            
            if game_title:
                detected_games.add((game_title, game_id or "N/A"))
            
            if game_title and game_id and last_update and local_timestamp:
                last_update_timestamp = time.mktime(datetime.strptime(last_update.split("T")[0], '%Y-%m-%d').timetuple())
                
                # Debug prints to show the timestamps and comparison
                print(f"Game: {game_title}")
                print(f"Local Timestamp: {local_timestamp} ({datetime.fromtimestamp(local_timestamp)})")
                print(f"Last Update Timestamp: {last_update_timestamp} ({datetime.fromtimestamp(last_update_timestamp)})")
                
                time_difference = last_update_timestamp - local_timestamp
                print(f"Time Difference: {time_difference}")
                print(f"Math: {last_update_timestamp} - {local_timestamp} = {time_difference}")
                
                if time_difference > 0:
                    local_date = datetime.fromtimestamp(local_timestamp).strftime('%Y-%m-%d')
                    last_update_date = datetime.fromtimestamp(last_update_timestamp).strftime('%Y-%m-%d')
                    outdated_games.append((game_title, local_date, last_update_date, game_slug))
                    print(f"Marked as outdated: {game_title}")
                else:
                    print(f"Up to date: {game_title}")
    
    return outdated_games, list(detected_games)

def main():
    """Main function to handle user interaction and processing."""
    choice = input("Do you want to scan a directory (1) or generate .name files (2)? ").strip()
    
    if choice == "2":
        output_directory = input("Enter the output directory for .name files: ").strip()
        generate_name_files(output_directory)
        return
    
    directory = input("Enter the path to your GOG installers folder: ").strip()
    if not os.path.isdir(directory):
        print("Invalid directory. Please enter a valid folder path.")
        return
    
    outdated_games, detected_games = scan_directory(directory)
    
    if detected_games:
        detected_games = sorted(detected_games, key=lambda x: x[0].lower())
        print("\nDetected Games:")
        for title, game_id in detected_games:
            print(f"{title} (ID: {game_id})")
    
    if outdated_games:
        outdated_games = sorted(outdated_games, key=lambda x: x[0].lower())
        print("\nOutdated Games Found:")
        for i, (title, local_date, latest, game_slug) in enumerate(outdated_games, start=1):
            print(f"{i}. {title} (Local Date: {local_date} -> Latest: {latest})")
        
        open_pages = input("\nWould you like to open the pages for these games? (y/n): ").strip().lower()
        if open_pages == 'y':
            for _, _, _, game_slug in outdated_games:
                webbrowser.open(f"{GOG_GAME_URL}{game_slug}")
    else:
        print("\nAll games are up to date!")

if __name__ == "__main__":
    main()