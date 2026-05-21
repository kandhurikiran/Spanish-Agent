import os
import base64
from datetime import date
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

YOUR_EMAIL = os.getenv('YOUR_EMAIL')

def send_quiz_email(gmail, quiz_session_id: int, word_count: int, app_url: str):
    """Send email with link to today's quiz"""
    
    today = date.today().strftime('%B %d, %Y')
    quiz_url = f"{app_url}/quiz/{quiz_session_id}"
    
    html = f"""
    <html>
    <body style="background:#11111b;font-family:Arial,sans-serif;padding:20px;max-width:600px;margin:0 auto;">
        
        <h1 style="color:#cba6f7;text-align:center;">🇪🇸 Daily Spanish Quiz</h1>
        <p style="color:#6c7086;text-align:center;">{today}</p>
        
        <div style="background:#1e1e2e;border-radius:12px;padding:30px;text-align:center;margin:20px 0;">
            <p style="color:#cdd6f4;font-size:18px;">
                You have <strong style="color:#cba6f7;">{word_count} words</strong> to review today
            </p>
            <a href="{quiz_url}" 
               style="background:#cba6f7;color:#11111b;padding:15px 40px;
                      border-radius:8px;text-decoration:none;font-weight:bold;
                      font-size:18px;display:inline-block;margin-top:15px;">
                Start Quiz →
            </a>
        </div>
        
        <p style="color:#6c7086;text-align:center;font-size:12px;">
            Complete the quiz to maintain your streak! 🔥
        </p>
        
    </body>
    </html>
    """
    
    message_body = f"""From: {YOUR_EMAIL}
To: {YOUR_EMAIL}
Subject: 🇪🇸 Spanish Quiz — {today} ({word_count} words)
MIME-Version: 1.0
Content-Type: text/html; charset=utf-8

{html}"""
    
    encoded = base64.urlsafe_b64encode(message_body.encode()).decode()
    message = {'raw': encoded}
    gmail.users().messages().send(userId='me', body=message).execute()
    print(f"Quiz email sent — {word_count} words — {quiz_url}")