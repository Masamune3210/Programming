import os
import re
import json
import webbrowser
import requests
from datetime import datetime, timedelta
import subprocess

GOG_API_URL = "https://gog-games.to/api/web/query-game/"
GOG_GAME_URL = "https://gog-games.to/game/"
DATABASE_FILE = "gog_games_database.json"
REAL_DEBRID_API_URL = "https://api.real-debrid.com/rest/1.0/torrents/addMagnet"
REAL_DEBRID_SELECT_FILES_URL = "https://api.real-debrid.com/rest/1.0/torrents/selectFiles"
REAL_DEBRID_INFO_URL = "https://api.real-debrid.com/rest/1.0/torrents/info"
REAL_DEBRID_API_TOKEN = "P3U5O4TYSVICKVHDZH7F6ZQKWMTTYMTUU3OXJMAHHEF7HGREX24Q"  # Replace with your Real-Debrid API token

def load_game_database():
    """Load GOG games database from JSON file."""
    if os.path.isfile(DATABASE_FILE):
        with open(DATABASE_FILE, 'r', encoding='utf-8') as db_file:
            return json.load(db_file)
    return []

game_database = load_game_database()

def check_database_age():
    """Check the age of the database file and update if older than a week or if not found."""
    if not os.path.isfile(DATABASE_FILE) or datetime.now() - datetime.fromtimestamp(os.path.getmtime(DATABASE_FILE)) > timedelta(weeks=1):
        print("Database is either not found or older than a week. Updating...")
        subprocess.run(["python", "fetch_gogto_games.py"], check=True)
        return True
    return False

def find_game_in_database_by_slug(slug):
    """Find game information in the local database by slug."""
    normalized_slug = slug.strip().lower()
    for game in game_database:
        db_slug = game["slug"].strip().lower()
        if db_slug == normalized_slug:
            return game["title"], game["id"], game["slug"], game.get("last_update"), game.get("infohash")
    return slug, None, None, None, None

def extract_game_info_from_name_file(game_folder_path):
    """Check for a .name file in the game folder and return the proper title from the database."""
    for entry in os.scandir(game_folder_path):
        if entry.is_file() and entry.name.endswith(".name"):
            with open(entry.path, 'r', encoding='utf-8') as name_file:
                raw_slug = name_file.read().strip()
                return find_game_in_database_by_slug(raw_slug)
    return None, None, None, None, None

def extract_game_info(filename):
    """Extract game title and ID from the filename."""
    match = re.search(r"setup_(.+?)_([\d\.r]+)(?:_|\s)\((\d+)\)", filename)
    if match:
        title = match.group(1).replace("_", " ").title()
        return find_game_in_database_by_slug(title)
    return None, None, None, None, None

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
    magnet_links = []

    for game_folder in os.scandir(directory):
        if game_folder.is_dir():
            if "[FitGirl Repacks]" in game_folder.name or "[DODI Repacks]" in game_folder.name:
                print(f"Skipping folder: {game_folder.name}")  # Debug print
                continue

            installer_entry = None
            # First, try to extract game info from the .name file.
            game_title, game_id, game_slug, last_update, infohash = extract_game_info_from_name_file(game_folder.path)

            # If .name file did not yield game info, search for the installer exe.
            if not game_title:
                for entry in os.scandir(game_folder.path):
                    if entry.is_file() and entry.name.startswith("setup_") and entry.name.endswith(".exe"):
                        game_title, game_id, game_slug, last_update, infohash = extract_game_info(entry.name)
                        if game_title:
                            installer_entry = entry
                            break
            else:
                # When .name file is used, still try to grab one installer file for the date.
                for entry in os.scandir(game_folder.path):
                    if entry.is_file() and entry.name.startswith("setup_") and entry.name.endswith(".exe"):
                        installer_entry = entry
                        break

            if game_title:
                detected_games.add((game_title, game_id or "N/A"))

            # Only use the date of one installer file per folder (installer_entry)
            if game_title and game_id and last_update and installer_entry:
                local_date = datetime.fromtimestamp(installer_entry.stat().st_mtime)
                last_update_time = datetime.strptime(last_update.split("T")[0], '%Y-%m-%d')

                # Convert to Unix epoch
                local_epoch = local_date.timestamp()
                last_update_epoch = last_update_time.timestamp()

                # Introduce a grace period of 3 days (in seconds)
                grace_seconds = 3 * 24 * 60 * 60  # 259200 seconds

                # Check if the difference is within the grace period
                if last_update_epoch - local_epoch <= grace_seconds:
                    # Game is considered up to date
                    continue
                else:
                    outdated_games.append((game_title, local_date.strftime('%Y-%m-%d'), last_update.split("T")[0], game_slug, infohash))
                    if infohash:
                        magnet_links.append(f"magnet:?xt=urn:btih:{infohash}")

    return outdated_games, list(detected_games), magnet_links

def get_torrent_info(torrent_id):
    """Get torrent information from Real-Debrid."""
    headers = {
        "Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"
    }
    response = requests.get(f"{REAL_DEBRID_INFO_URL}/{torrent_id}", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get torrent info for ID: {torrent_id}")
        print(f"Response: {response.status_code} - {response.text}")
        return None

def add_magnet_to_real_debrid(title,magnet_link):
    """Add a magnet link to Real-Debrid and select all files if available."""
    headers = {
        "Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"
    }
    data = {
        "magnet": magnet_link
    }
    response = requests.post(REAL_DEBRID_API_URL, headers=headers, data=data)
    if response.status_code == 201:
        print(f"{title}: {magnet_link}")
        torrent_id = response.json().get("id")
        if torrent_id:
            torrent_info = get_torrent_info(torrent_id)
            if torrent_info and torrent_info.get("files"):
                select_files(torrent_id)
            else:
                print(f"No files found for torrent ID: {torrent_id}, skipping file selection.")
    else:
        print(f"Failed to add magnet link to Real-Debrid: {magnet_link}")
        print(f"Response: {response.status_code} - {response.text}")

def select_files(torrent_id):
    """Select all files for the given torrent ID in Real-Debrid."""
    headers = {
        "Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"
    }
    data = {
        "files": "all"
    }
    response = requests.post(f"{REAL_DEBRID_SELECT_FILES_URL}/{torrent_id}", headers=headers, data=data)
    if response.status_code == 204:
        print(f"Successfully selected all files for torrent ID: {torrent_id}")
    else:
        print(f"Failed to select files for torrent ID: {torrent_id}")
        print(f"Response: {response.status_code} - {response.text}")

def main():
    """Main function to handle user interaction and processing."""
    if check_database_age():
        global game_database
        game_database = load_game_database()

    choice = input("Do you want to scan a directory (1) or generate .name files (2)? ").strip()
    
    if choice == "2":
        output_directory = input("Enter the output directory for .name files: ").strip()
        generate_name_files(output_directory)
        return
    
    directory = input("Enter the path to your GOG installers folder: ").strip()
    if not os.path.isdir(directory):
        print("Invalid directory. Please enter a valid folder path.")
        return
    
    outdated_games, detected_games, magnet_links = scan_directory(directory)
    
    if detected_games:
        detected_games.sort(key=lambda x: x[0].lower())
        print("\nDetected Games:")
        for title, game_id in detected_games:
            print(f"{title} (ID: {game_id})")
    
    if outdated_games:
        print("\nOutdated Games Found:")
        for i, (title, local_date, latest, game_slug, infohash) in enumerate(outdated_games, start=1):
            print(f"{i}. {title} (Local Date: {local_date} -> Latest: {latest})")
        
        action_choice = input("\nDo you want to send magnets to Real-Debrid (1) or open game pages (2)? ").strip()
        
        if action_choice == "1":
            if magnet_links:
                print("\nAdding Magnet Links to Real-Debrid:")
                for title, link in zip([game[0] for game in outdated_games], magnet_links):
                    add_magnet_to_real_debrid(title, link)
            
            open_pages = input("\nWould you like to open the pages for the games missing infohashes? (y/n): ").strip().lower()
            if open_pages == 'y':
                for _, _, _, game_slug, infohash in outdated_games:
                    if not infohash:
                        webbrowser.open(f"{GOG_GAME_URL}{game_slug}")
        elif action_choice == "2":
            for _, _, _, game_slug, _ in outdated_games:
                webbrowser.open(f"{GOG_GAME_URL}{game_slug}")
    else:
        print("\nAll games are up to date!")

if __name__ == "__main__":
    main()