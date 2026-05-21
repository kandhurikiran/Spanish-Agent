import os
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from youtube_transcript_api import YouTubeTranscriptApi

SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

DREAMING_SPANISH_CHANNEL_ID = 'UCouyFdE9-Lrjo3M_2idKq1A'

def get_google_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_todays_videos(youtube):
    """Get Dreaming Spanish videos you liked today"""
    today = datetime.now(timezone.utc).date()
    
    request = youtube.playlistItems().list(
        part='snippet,contentDetails',
        playlistId='LL',  # LL = Liked Videos playlist
        maxResults=50
    )
    response = request.execute()
    
    videos = []
    for item in response.get('items', []):
        # Check if liked today
        liked_at = item['snippet']['publishedAt']  # when you liked it
        liked_date = datetime.fromisoformat(
            liked_at.replace('Z', '+00:00')
        ).date()
        
        if liked_date != today:
            continue  # skip if not liked today
        
        # Check if from Dreaming Spanish
        channel_id = item['snippet']['videoOwnerChannelId']
        if channel_id != DREAMING_SPANISH_CHANNEL_ID:
            continue  # skip if not Dreaming Spanish
        
        video_id = item['contentDetails']['videoId']
        title = item['snippet']['title']
        videos.append({
            'video_id': video_id,
            'title': title
        })
        print(f"Found liked video: {title}")
    
    return videos

def get_transcript(video_id: str):
    """Get Spanish transcript from video"""
    try:
        ytt = YouTubeTranscriptApi()
        transcript = ytt.fetch(video_id, languages=['es'])
        text = ' '.join([t.text for t in transcript])
        
        # Smart sampling — beginning, middle, end
        words = text.split()
        if len(words) > 1000:
            sample = (
                words[:300] + 
                words[len(words)//2 - 150:len(words)//2 + 150] + 
                words[-300:]
            )
            text = ' '.join(sample)
        
        return text
    except Exception as e:
        print(f"Transcript error: {e}")
        return None

def build_youtube_client():
    creds = get_google_credentials()
    return build('youtube', 'v3', credentials=creds)

def build_gmail_client():
    creds = get_google_credentials()
    return build('gmail', 'v1', credentials=creds)