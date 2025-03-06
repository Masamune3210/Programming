import requests
import json

# URL of the API endpoint
API_URL = "https://gog-games.to/api/web/all-games"

# Function to fetch and process the data from the API
def fetch_games():
    response = requests.get(API_URL)

    if response.status_code == 200:
        # Parse the response JSON
        games = response.json()

        # Prepare a list of games with only id, title, and slug
        game_data = []
        for game in games:
            game_data.append({
                "id": game["id"],
                "slug": game["slug"],
                "title": game["title"],
                "developer": game["developer"],
                "publisher": game["publisher"],
                "last_update": game["last_update"],
                "infohash": game["infohash"]
            })

        # Save the extracted data to a JSON file
        with open("gog_games_database.json", "w", encoding="utf-8") as f:
            json.dump(game_data, f, indent=4, ensure_ascii=False)

        print(f"Successfully saved {len(game_data)} games to 'gog_games_database.json'")
    else:
        print(f"Failed to fetch data. Status Code: {response.status_code}")

# Main function to run the script
def main():
    fetch_games()

# Run the script
if __name__ == "__main__":
    main()
