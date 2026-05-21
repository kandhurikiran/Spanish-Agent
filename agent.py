import os
import json
import base64
import datetime
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import anthropic

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
DREAMING_SPANISH_CHANNEL_ID = 'UCouyFdE9-Lrjo3M_2idKq1A'
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]
YOUR_EMAIL = 'kandhuri4294@gmail.com'

# ── Setup Gemini ──────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Google Auth ───────────────────────────────────────────────────────────
def get_google_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

# ── Get latest video from Dreaming Spanish ────────────────────────────────
def get_latest_video(youtube):
    request = youtube.search().list(
        part='snippet',
        channelId=DREAMING_SPANISH_CHANNEL_ID,
        maxResults=1,
        order='date',
        type='video'
    )
    response = request.execute()
    if response['items']:
        video = response['items'][0]
        video_id = video['id']['videoId']
        title = video['snippet']['title']
        print(f"Latest video: {title}")
        return video_id, title
    return None, None

# ── Get transcript ────────────────────────────────────────────────────────
def get_transcript(video_id):
    try:
        ytt = YouTubeTranscriptApi()
        transcript = ytt.fetch(video_id, languages=['es'])
        text = ' '.join([t.text for t in transcript])
        return text[:3000]
    except Exception as e:
        print(f"Transcript error: {e}")
        return None

# ── Extract vocabulary using Gemini ───────────────────────────────────────
def extract_vocabulary(transcript, video_title):
    prompt = f"""
    You are a Spanish teacher. From this Spanish transcript, extract exactly 10 vocabulary words 
    suitable for a complete beginner (A1 level).
    
    Choose common, useful everyday words. For each word provide:
    - The Spanish word
    - English translation
    - A simple example sentence in Spanish
    - English translation of the example sentence
    
    Return ONLY valid JSON in this exact format:
    {{
        "video_title": "{video_title}",
        "words": [
            {{
                "spanish": "hola",
                "english": "hello",
                "example_es": "Hola, como estas?",
                "example_en": "Hello, how are you?"
            }}
        ]
    }}
    
    Transcript: {transcript}
    """
    response = claude.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1000,
        messages=[{'role': 'user', 'content': prompt}]
    )
    text = response.content[0].text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    return json.loads(text.strip())

# ── Build HTML email ──────────────────────────────────────────────────────
def build_email_html(vocab_data):
    today = datetime.date.today().strftime('%B %d, %Y')
    words_html = ''
    for word in vocab_data['words']:
        words_html += f"""
        <div style="background:#1e1e2e;border-radius:12px;padding:20px;margin:10px 0;border-left:4px solid #cba6f7;">
            <div style="font-size:28px;font-weight:bold;color:#cba6f7;">{word['spanish']}</div>
            <div style="font-size:18px;color:#a6e3a1;margin:5px 0;">{word['english']}</div>
            <div style="font-size:14px;color:#cdd6f4;margin-top:10px;font-style:italic;">"{word['example_es']}"</div>
            <div style="font-size:13px;color:#6c7086;">"{word['example_en']}"</div>
        </div>
        """

    html = f"""
    <html>
    <body style="background:#11111b;font-family:Arial,sans-serif;padding:20px;max-width:600px;margin:0 auto;">
        <h1 style="color:#cba6f7;text-align:center;">🇪🇸 Daily Spanish Vocabulary</h1>
        <p style="color:#6c7086;text-align:center;">{today}</p>
        <p style="color:#cdd6f4;text-align:center;">From: <em>{vocab_data['video_title']}</em></p>
        <hr style="border-color:#313244;margin:20px 0;">
        {words_html}
        <p style="color:#6c7086;text-align:center;margin-top:30px;font-size:12px;">
            Keep learning! 🌟
        </p>
    </body>
    </html>
    """
    return html

# ── Send email ────────────────────────────────────────────────────────────
def send_email(gmail, html_content, subject):
    message_body = f"""From: {YOUR_EMAIL}
To: {YOUR_EMAIL}
Subject: {subject}
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

{html_content}"""

    encoded = base64.urlsafe_b64encode(message_body.encode()).decode()
    message = {'raw': encoded}
    gmail.users().messages().send(userId='me', body=message).execute()
    print("Email sent successfully!")

# ── Main agent loop ───────────────────────────────────────────────────────
def run_agent():
    print("🤖 Spanish Agent starting...")

    creds = get_google_credentials()
    youtube = build('youtube', 'v3', credentials=creds)
    gmail = build('gmail', 'v1', credentials=creds)

    video_id, title = get_latest_video(youtube)
    if not video_id:
        print("No video found")
        return

    transcript = get_transcript(video_id)
    if not transcript:
        print("No transcript available")
        return

    print("Extracting vocabulary with Claude...")
    vocab_data = extract_vocabulary(transcript, title)

    html = build_email_html(vocab_data)
    subject = f"🇪🇸 Spanish Words for {datetime.date.today().strftime('%B %d')}"
    send_email(gmail, html, subject)

    print("✅ Done!")

if __name__ == '__main__':
    run_agent()