import spotipy
from spotipy.oauth2 import SpotifyOAuth
from gpt4all import GPT4All

# ---------------- CONFIGURATION ---------------- #
model_path = "/Users/skylerchanuwc/Library/Application Support/nomic.ai/GPT4All/Meta-Llama-3-8B-Instruct.Q4_0.gguf"
gpt = GPT4All(model_path)
CLIENT_ID = "clientid"
CLIENT_SECRET = "clientsecret"
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
def create_playlist_on_spotify(song_list, playlist_name="AI Generated Playlist"):
    user_id = sp.me()["id"]
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=False)
    playlist_id = playlist["id"]

    track_uris = []
    for song in song_list:
        result = sp.search(q=song, type="track", limit=1)
        if result['tracks']['items']:
            track_uris.append(result['tracks']['items'][0]['uri'])

    if track_uris:
        sp.playlist_add_items(playlist_id, track_uris)
        print(f"✅ Created playlist '{playlist_name}' with {len(track_uris)} tracks!")
    else:
        print("❌ Couldn't find any of the suggested songs on Spotify.")
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

    If the user asks to create a playlist, output exactly in this format:
    ACTION: create_playlist
    PLAYLIST_NAME: (a nice playlist name)
    SONGS:
    - Song Name by Artist Name
    - Song Name by Artist Name
    (at least 10 songs)
    """

    response = gpt.generate(prompt)
    print("Bot:", response.strip())
     
    if "ACTION: create_playlist" in response:
        # Extract playlist name
        playlist_name = "AI Playlist"
        if "PLAYLIST_NAME:" in response:
            lines = response.splitlines()
            for line in lines:
                if line.startswith("PLAYLIST_NAME:"):
                    playlist_name = line.replace("PLAYLIST_NAME:", "").strip()

        # Extract song list
        songs = []
        if "SONGS:" in response:
            parts = response.split("SONGS:")[1].strip().split("\n")
            for line in parts:
                if line.startswith("-"):
                    songs.append(line.replace("-", "").strip())

        if songs:
            create_playlist_on_spotify(songs, playlist_name)
