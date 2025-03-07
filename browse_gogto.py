import os
import json
import webbrowser
import requests
from datetime import datetime, timedelta

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

def browse_games(game_database, selected_games, page_size=30):
    """Browse the list of games with pagination."""
    total_games = len(game_database)
    total_pages = (total_games + page_size - 1) // page_size

    current_page = 0
    while True:
        if len(selected_games) > 10:
            page_size = 20
        else:
            page_size = 30

        start_index = current_page * page_size
        end_index = min(start_index + page_size, total_games)
        for i in range(start_index, end_index):
            game = game_database[i]
            print(f"{i + 1}. {game['title']} (ID: {game['id']})")

        print(f"\nPage {current_page + 1} of {total_pages}")
        if current_page > 0:
            print("p. Previous page")
        if current_page < total_pages - 1:
            print("n. Next page")
        print("q. Quit browsing")
        print("s. Select games")

        if selected_games:
            print("\nSelected Games:")
            for game in selected_games:
                print(f"- {game['title']} (ID: {game['id']})")

        choice = input("Enter your choice: ").strip().lower()
        if choice == 'n' and current_page < total_pages - 1:
            current_page += 1
        elif choice == 'p' and current_page > 0:
            current_page -= 1
        elif choice == 'q':
            break
        elif choice == 's':
            selected_indices = input("Enter the numbers of the games you want to select (comma-separated): ").strip()
            selected_indices = [int(i) - 1 for i in selected_indices.split(",")]
            selected_games.extend([game_database[i] for i in selected_indices])
        else:
            print("Invalid choice. Please enter 'n', 'p', 'q', or 's'.")

    return selected_games

def search_games(game_database, term):
    """Search games by term."""
    results = [game for game in game_database if term.lower() in game['title'].lower()]
    for i, game in enumerate(results, start=1):
        print(f"{i}. {game['title']} (ID: {game['id']})")
    return results

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

def add_magnet_to_real_debrid(magnet_link):
    """Add a magnet link to Real-Debrid and select all files if available."""
    headers = {
        "Authorization": f"Bearer {REAL_DEBRID_API_TOKEN}"
    }
    data = {
        "magnet": magnet_link
    }
    response = requests.post(REAL_DEBRID_API_URL, headers=headers, data=data)
    if response.status_code == 201:
        print(f"Successfully added magnet link to Real-Debrid: {magnet_link}")
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
    global game_database
    game_database = load_game_database()

    choice = input("Do you want to browse the list of games (1) or search by term (2)? ").strip()
    
    selected_games = []
    if choice == "1":
        selected_games = browse_games(game_database, selected_games)
    elif choice == "2":
        term = input("Enter the search term: ").strip()
        results = search_games(game_database, term)
        if not results:
            print("No games found matching the search term.")
            return
        selected_indices = input("Enter the numbers of the games you want to select (comma-separated): ").strip()
        selected_indices = [int(i) - 1 for i in selected_indices.split(",")]
        selected_games = [results[i] for i in selected_indices]
    else:
        print("Invalid choice. Please enter 1 or 2.")
        return

    magnet_links = []

    for game in selected_games:
        if game.get("infohash"):
            magnet_links.append(f"magnet:?xt=urn:btih:{game['infohash']}")
        else:
            webbrowser.open(f"{GOG_GAME_URL}{game['slug']}")

    if magnet_links:
        print("\nAdding Magnet Links to Real-Debrid:")
        for link in magnet_links:
            add_magnet_to_real_debrid(link)

if __name__ == "__main__":
    main()