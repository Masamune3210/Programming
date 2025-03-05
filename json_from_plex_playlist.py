import requests
import json
import xml.etree.ElementTree as ET

DOCKER_MOUNT_PATH = "/data/"
WINDOWS_MOUNT_PATH = "Y:\\Media\\Plex Media\\"
PLEX_AUTH_TOKEN = "Mr2JPNmxYUGA6ZBhXs25"
PLEX_IP_ADDRESS = "192.168.0.48"

def get_playlists():
    url = f"http://{PLEX_IP_ADDRESS}:32400/playlists?X-Plex-Token={PLEX_AUTH_TOKEN}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch playlists. HTTP {response.status_code}")
        return []
    
    try:
        root = ET.fromstring(response.text)
        return [{"title": p.get("title"), "ratingKey": p.get("ratingKey")} for p in root.findall(".//Playlist")]
    except ET.ParseError:
        print("Failed to parse XML response from Plex.")
        return []

def get_playlist_items(playlist_key):
    url = f"http://{PLEX_IP_ADDRESS}:32400/playlists/{playlist_key}/items?X-Plex-Token={PLEX_AUTH_TOKEN}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch playlist items. HTTP {response.status_code}")
        return []
    
    try:
        root = ET.fromstring(response.text)
        items = []
        for item in root.findall(".//Video"):
            media = item.find("Media")
            part = media.find("Part") if media is not None else None
            file_path = part.get("file") if part is not None else "Unknown"
            file_size = part.get("size", 0) if part is not None else 0

            # Convert Docker path to Windows path
            if file_path.startswith(DOCKER_MOUNT_PATH):
                file_path = file_path.replace(DOCKER_MOUNT_PATH, WINDOWS_MOUNT_PATH).replace("/", "\\")

            items.append({"file": file_path, "size": file_size})
        return items
    except ET.ParseError:
        print("Failed to parse XML response from Plex.")
        return []

def main():
    playlists = get_playlists()
    if not playlists:
        print("No playlists found.")
        return
    
    print("Available Playlists:")
    for idx, playlist in enumerate(playlists):
        print(f"{idx + 1}: {playlist.get('title', 'Unknown')}")
    
    choice = int(input("Select a playlist by number: ")) - 1
    if choice < 0 or choice >= len(playlists):
        print("Invalid choice.")
        return
    
    selected_playlist = playlists[choice]
    playlist_key = selected_playlist['ratingKey']
    items = get_playlist_items(playlist_key)
    
    output_data = {
        "encoder": "",
        "ignored_encoders": [],
        "files": items
    }
    
    with open("playlist_info.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)
    
    print("Playlist information saved to playlist_info.json")

if __name__ == "__main__":
    main()