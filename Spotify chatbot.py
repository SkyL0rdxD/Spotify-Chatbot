import spotipy
from spotipy.oauth2 import SpotifyOAuth
model_path = "/Users/skylerchanuwc/Library/Application Support/nomic.ai/GPT4All/Meta-Llama-3-8B-Instruct.Q4_0.gguf"
from gpt4all import GPT4All
gpt = GPT4All(model_path)
CLIENT_ID = "clientid"
CLIENT_SECRET = "clientsecret"
REDIRECT_URI = "http://127.0.0.1:8888/callback"  # Loopback IP
SCOPE = (
    "ugc-image-upload "
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "app-remote-control "
    "streaming "
    "playlist-read-private "
    "playlist-read-collaborative "
    "playlist-modify-private "
    "playlist-modify-public "
    "user-follow-modify "
    "user-follow-read "
    "user-read-playback-position "
    "user-top-read "
    "user-read-recently-played "
    "user-library-modify "
    "user-library-read "
    "user-read-email "
    "user-read-private"
)
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path="spotify_token.json"
))
def get_intent(user_input):
    prompt = f"""
    Classify the question into one of:
    - recent_songs
    - top_artists
    - top_songs
    - play_song
    - create_playlist
    If it's not related to Spotify, respond naturally as a chatbot.
    User question: {user_input}
    Intent:
    """
    with gpt.chat_session():
        response = gpt.generate(prompt)
    return response.strip().lower()

def answer_question(intent, user_input):
    if "recent" in intent:
        results = sp.current_user_recently_played(limit=5)
        songs = [f"{item['track']['name']} by {item['track']['artists'][0]['name']}" for item in results['items']]
        return "Your recently played songs:\n" + "\n".join(songs)

    elif "top_artists" in intent:
        results = sp.current_user_top_artists(limit=5)
        artists = [artist['name'] for artist in results['items']]
        return "Your top artists:\n" + "\n".join(artists)

    elif "top_songs" in intent:
        # Extract number if user asked for top X
        import re
        match = re.search(r"\d+", user_input)
        limit = int(match.group()) if match else 5  # Default 5 if no number
        results = sp.current_user_top_tracks(limit=limit)
        tracks = [f"{track['name']} by {track['artists'][0]['name']}" for track in results['items']]
        return f"Your top {limit} songs:\n" + "\n".join(tracks)

    elif "play_song" in intent:
        results = sp.search(q=user_input, limit=1, type="track")
        if results['tracks']['items']:
            track_uri = results['tracks']['items'][0]['uri']
            sp.start_playback(uris=[track_uri])
            return f"Playing {results['tracks']['items'][0]['name']}!"
        else:
            return "Couldn't find that song."

    elif "create_playlist" in intent:
        user_id = sp.me()["id"]

        # Step 1: Interpret playlist type (mood, recent, top)
        interpretation_prompt = f"""
        The user wants a Spotify playlist. Options:
        - mood:<mood_name>
        - recent
        - top
        Analyze: {user_input}
        """
        llm_response = gpt.chat(prompt=interpretation_prompt).strip().lower()

        playlist_type = "mood"
        mood = "random"

        if llm_response.startswith("mood:"):
            playlist_type = "mood"
            mood = llm_response.replace("mood:", "").strip()
        elif "recent" in llm_response:
            playlist_type = "recent"
        elif "top" in llm_response:
            playlist_type = "top"

        playlist_name = f"{mood.title()} Playlist" if playlist_type == "mood" else \
                        ("Inspired by Your Recent Songs" if playlist_type == "recent" else "Inspired by Your Top Songs")

        # Create playlist
        playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=False)
        playlist_id = playlist["id"]

        track_uris = []

        if playlist_type == "mood":
            # Standard mood search
            results = sp.search(q=mood, type="track", limit=15)
            track_uris = [track["uri"] for track in results["tracks"]["items"]]

        elif playlist_type in ["recent", "top"]:
            # Fetch user's reference tracks
            if playlist_type == "recent":
                base_tracks = sp.current_user_recently_played(limit=5)
                base_list = [item['track']['name'] + " by " + item['track']['artists'][0]['name'] for item in base_tracks['items']]
            else:
                base_tracks = sp.current_user_top_tracks(limit=5)
                base_list = [track['name'] + " by " + track['artists'][0]['name'] for track in base_tracks['items']]

            # Step 2: Ask LLM to suggest similar songs
            suggestion_prompt = f"""
            Suggest 10 popular songs that are similar in vibe to these songs:
            {', '.join(base_list)}
            Format as: Song Name by Artist.
            Only list songs, no extra text.
            """
            suggestions = gpt.chat(prompt=suggestion_prompt).strip().split("\n")

            # Step 3: Search Spotify for suggested songs
            for suggestion in suggestions:
                query = suggestion.strip()
                if query:
                    result = sp.search(q=query, type="track", limit=1)
                    if result['tracks']['items']:
                        track_uris.append(result['tracks']['items'][0]['uri'])

            # Step 4: Add tracks to playlist
                if track_uris:
                    sp.playlist_add_items(playlist_id, track_uris[:30])  # Limit to 30 tracks
                    return f"Created '{playlist_name}' with {len(track_uris[:30])} new tracks similar to your taste!"
                else:
                    return "Couldn't find enough tracks for that playlist."
    else:
        return gpt.generate(f"User: {user_input}\nBot:")
print("Spotify Chatbot is ready! Type 'exit' to quit.")
while True:
    user_input = input("You: ") 
    if user_input.lower() in ["exit", "quit"]:
        print("Bot: Goodbye!")
        break
    intent = get_intent(user_input)
    response = answer_question(intent, user_input)
    print("Bot:", response)
