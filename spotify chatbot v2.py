import spotipy
from spotipy.oauth2 import SpotifyOAuth
from gpt4all import GPT4All

# ---------------- CONFIGURATION ---------------- #
model_path = "/Users/skylerchanuwc/Library/Application Support/nomic.ai/GPT4All/Meta-Llama-3-8B-Instruct.Q4_0.gguf"
gpt = GPT4All(model_path)
CLIENT_ID = "3f2226e70fe04a778b0c81cb9c000b20"
CLIENT_SECRET = "1577c2f4cf424784bfdec2a94f639687"
#CLIENT_ID = "YOUR_NEW_CLIENT_ID" 
#CLIENT_SECRET = "YOUR_NEW_CLIENT_SECRET"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPE = (
    "user-read-playback-state user-modify-playback-state user-read-currently-playing "
    "playlist-modify-public playlist-modify-private user-read-recently-played user-top-read "
    "playlist-read-private playlist-read-collaborative"
)

# Spotify Auth
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path="spotify_token.json"
))

# ---------------- FETCH SPOTIFY DATA ---------------- #
def get_all_spotify_data():
    """Fetch user's Spotify data and return as a structured dictionary."""
    data = {}

    # Recent tracks
    data['recent_tracks'] = [
        f"{item['track']['name']} by {item['track']['artists'][0]['name']}"
        for item in sp.current_user_recently_played(limit=10)['items']
    ]

    # Top tracks
    data['top_tracks'] = [
        f"{track['name']} by {track['artists'][0]['name']}"
        for track in sp.current_user_top_tracks(limit=10)['items']
    ]

    # Top artists
    data['top_artists'] = [
        artist['name'] for artist in sp.current_user_top_artists(limit=10)['items']
    ]

    # Playlists
    playlists = sp.current_user_playlists(limit=5)['items']
    data['playlists'] = [pl['name'] for pl in playlists]

    return data

# ---------------- CHATBOT LOOP ---------------- #
spotify_data = get_all_spotify_data()

print("Spotify + GPT4All Chatbot is ready! Type 'exit' to quit.")
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("Bot: Goodbye!")
        break

    # Build dynamic prompt for LLM
    prompt = f"""
    You are a helpful music assistant that interprets a user's spotify data. Here is the user's Spotify data:

    Recent Tracks: {spotify_data['recent_tracks']}
    Top Tracks: {spotify_data['top_tracks']}
    Top Artists: {spotify_data['top_artists']}
    Playlists: {spotify_data['playlists']}

    Question: {user_input}

    Answer naturally based on the data.
    - If user asks for top songs, mention them from the data.
    - If user asks for recent songs, mention them from the data.
    - If user asks for favorite artist, infer from top_artists.
    - If user asks for recommendations, suggest related artists or songs.
    - If user asks to create a playlist, list 10 songs you recommend.
    - Do NOT explain how you formed the answer.
    - Do NOT give instructions or examples.
    - If the question asks for top songs, use 'Top Tracks' list.
    - Respond naturally, like a friend talking.
    Respond conversationally.
    """

    response = gpt.generate(prompt)
    print("Bot:", response.strip())