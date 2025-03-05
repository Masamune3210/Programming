import os
import re
import requests
import webbrowser

gog_api_url = "https://gog-games.to/api/games"

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

def get_latest_version(game_title):
    response = requests.get(f"{gog_api_url}?search={game_title}")
    print(f"API Request: {gog_api_url}?search={game_title} -> Status: {response.status_code}")  # Debug print
    if response.status_code == 200:
        print(f"API Response: {response.text[:200]}...")  # Debug print (truncated for readability)
        games = response.json()
        for game in games:
            if game_title.lower() in game['title'].lower():
                return game['latest_version'], game['url']
    return None, None

def scan_directory(directory):
    outdated_games = []
    for entry in os.scandir(directory):  # Only scan one level deep
        if entry.is_dir() and "[FitGirl Repack]" in entry.name:
            print(f"Skipping folder: {entry.name}")  # Debug print
            continue
        if entry.is_file() and entry.name.startswith("setup_") and entry.name.endswith(")"):
            print(f"Checking: {entry.name}")  # Debug print
            game_title, local_version, game_id = extract_game_info(entry.name)
            if game_title and local_version:
                latest_version, game_url = get_latest_version(game_title)
                print(f"Detected: {game_title} (Local: {local_version}, Remote: {latest_version if latest_version else 'Unknown'})")
                if latest_version and latest_version != local_version:
                    outdated_games.append((game_title, local_version, latest_version, game_url))
    return outdated_games

def main():
    directory = input("Enter the path to your GOG installers folder: ").strip()
    if not os.path.isdir(directory):
        print("Invalid directory. Please enter a valid folder path.")
        return
    
    outdated_games = scan_directory(directory)
    
    if outdated_games:
        print("\nOutdated Games Found:")
        for i, (title, local, latest, url) in enumerate(outdated_games, start=1):
            print(f"{i}. {title} (Local: {local} -> Latest: {latest})")
        
        open_pages = input("\nWould you like to open the pages for these games? (y/n): ").strip().lower()
        if open_pages == 'y':
            for _, _, _, url in outdated_games:
                webbrowser.open(url)
    else:
        print("\nAll games are up to date!")

if __name__ == "__main__":
    main()
