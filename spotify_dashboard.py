import streamlit as st
import requests
import urllib.parse
from datetime import datetime, timedelta
import os

# try:
#     import stored_variables
#     CLIENT_ID = stored_variables.client_id
#     CLIENT_SECRET = stored_variables.client_secret
# except ImportError:
#     CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
#     CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

# # Use deployed URL if available, otherwise local
# if "STREAMLIT_SHARING" in os.environ or "STREAMLIT_CLOUD" in os.environ:
#     # This will be your deployed app URL - update after deployment
#     REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://anikaranam-spotify-stats-dashboard.streamlit.app")
# else:
#     REDIRECT_URI = "http://127.0.0.1:8501"
# SPOTIFY_URI = 'https://api.spotify.com/v1/me'


# Try to import from stored_variables (local), fallback to environment variables (deployment)
try:
    import stored_variables
    CLIENT_ID = stored_variables.client_id
    CLIENT_SECRET = stored_variables.client_secret
except ImportError:
    CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
    CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

# Check if running on Streamlit Cloud or locally
# On Streamlit Cloud, REDIRECT_URI must be set in secrets
REDIRECT_URI = os.environ.get("REDIRECT_URI")

# If REDIRECT_URI not set (local development), use local address
if not REDIRECT_URI:
    REDIRECT_URI = "http://127.0.0.1:8501"
SPOTIFY_URI = 'https://api.spotify.com/v1/me'

# Page config
st.set_page_config(page_title="Spotify Stats Dashboard", layout="wide")
st.subheader(f"Redirect URI: {REDIRECT_URI}")
st.subheader(f"Client ID: {CLIENT_ID}")
st.subheader(f"Client Secret: {CLIENT_SECRET}")

if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'token_expiry' not in st.session_state:
    st.session_state.token_expiry = None

def get_auth_url():
    """Generate Spotify authorization URL"""
    scope = "user-follow-read user-top-read"
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": 'https://anikaranam-spotify-stats-dashboard.streamlit.app',
        "scope": scope,
        "show_dialog": "true"
    }
    return f"{auth_url}?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(code):
    """Exchange authorization code for access token"""
    token_url = "https://accounts.spotify.com/api/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": 'https://anikaranam-spotify-stats-dashboard.streamlit.app',
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    response = requests.post(token_url, data=token_data, headers=token_headers)
    
    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("access_token"), token_data.get("expires_in")
    return None, None

def is_token_valid():
    """Check if current token is still valid"""
    if st.session_state.access_token and st.session_state.token_expiry:
        return datetime.now() < st.session_state.token_expiry
    return False

def get_spotify_data(endpoint, params=None):
    """Generic function to fetch data from Spotify API"""
    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
    response = requests.get(endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    return None

# Main app
st.title("How do you listen to music?")
st.subheader("A dashboard to track your Spotify listening habits")

# make sure authorization code exists and is valid
query_params = st.query_params
if "code" in query_params and not is_token_valid():
    code = query_params["code"]
    access_token, expires_in = exchange_code_for_token(code)
    
    if access_token:
        st.session_state.access_token = access_token
        st.session_state.token_expiry = datetime.now() + timedelta(seconds=expires_in)
        st.query_params.clear()
        st.rerun()
    else:
        st.error("Failed to get access token. Please try again.")

# Show login or dashboard
if not is_token_valid():
    st.write("### Tired of waiting for Spotify Wrapped?")
    st.write("Connect your Spotify account to look at your top artists, tracks, and followed artists.")
    st.write("")
    
    auth_url = get_auth_url()
    st.markdown(f'<a href="{auth_url}" target="_self"><button style="background-color: #1DB954; color: white; padding: 12px 24px; border: none; border-radius: 24px; font-size: 16px; font-weight: bold; cursor: pointer;">Connect with Spotify</button></a>', unsafe_allow_html=True)
    
    st.write("")
    st.write("**Note:** You'll be redirected to Spotify to authorize access. No personal data is stored.")

else:
    # Sidebar for config options
    with st.sidebar:
        st.write("### Settings")
        time_range = st.selectbox(
            "Time range",
            ["short_term", "medium_term", "long_term"],
            format_func=lambda x: {"short_term": "Last 4 Weeks", "medium_term": "Last 6 Months", "long_term": "All Time"}[x]
        )
        # limit = st.slider("Number of items", 5, 50, 20)
        # decided to hardcode the limit to 20 for now
        limit = 20

        if st.button("Logout"):
            st.session_state.access_token = None
            st.session_state.token_expiry = None
            st.rerun()

    # create tabs for different views
    tab1, tab2, tab3 = st.tabs(["Top artists", "Top tracks", "Followed artists"])

    with tab1:
        st.subheader("Your top artists")
        if time_range == "short_term":
            st.write("These are the artists you listened to the most in the last 4 weeks.")
        elif time_range == "medium_term":
            st.write("These are the artists you listened to the most in the last 6 months.")
        else:
            st.write("These are the artists you listened to the most all time.")
        top_artists_data = get_spotify_data(
            f"{SPOTIFY_URI}/top/artists",
            params={"time_range": time_range, "limit": limit}
        )
        
        if top_artists_data:
            artists = top_artists_data.get('items', [])
            
            # Display in columns
            cols = st.columns(2)
            for i, artist in enumerate(artists):
                genres = artist.get('genres', [])
                if "desi" in genres:
                    continue
                with cols[i % 2]:
                    with st.container():
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            if artist.get('images'):
                                st.image(artist['images'][0]['url'], width=80)
                        with col2:
                            st.write(f"**{i+1}. {artist.get('name')}**")
                            # st.write(f"Overall artist popularity: {artist.get('popularity')}/100", st.tooltip("This is a tooltip"))
                            st.markdown(f"<p>Overall artist popularity: {artist.get('popularity')}/100</p>", unsafe_allow_html=True, help="This is a 0 to 100 score tracking current popularity \nfor an artist across Spotify")
                            if artist.get('genres'):
                                st.caption(f"Genres: {', '.join(artist.get('genres', [])[:3])}")
                        st.write("")

    with tab2:
        st.subheader("Your top tracks")
        top_tracks_data = get_spotify_data(
            f"{SPOTIFY_URI}/top/tracks",
            params={"time_range": time_range, "limit": limit}
        )
        
        if top_tracks_data:
            tracks = top_tracks_data.get('items', [])
            
            for i, track in enumerate(tracks):
                col1, col2 = st.columns([1, 5])
                with col1:
                    if track.get('album', {}).get('images'):
                        st.image(track['album']['images'][0]['url'], width=60)
                with col2:
                    st.write(f"**{i+1}. {track.get('name')}**")
                    artists = ", ".join([a['name'] for a in track.get('artists', [])])
                    st.caption(f"by {artists}")
                st.divider()

    with tab3:
        st.subheader("Artists you follow")
        following_data = get_spotify_data(f"{SPOTIFY_URI}/following?type=artist")
        
        if following_data:
            artists = following_data.get('artists', {}).get('items', [])
            st.write(f"**Following {len(artists)} artists**")
            
            # Display in grid
            cols = st.columns(3)
            for i, artist in enumerate(artists):
                with cols[i % 3]:
                    if artist.get('images'):
                        st.image(artist['images'][0]['url'], use_container_width=True)
                    st.write(f"**{artist.get('name')}**")
                    st.caption(f"{artist.get('followers', {}).get('total', 0):,} followers")
                    st.write("")
