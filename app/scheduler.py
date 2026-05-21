import os
from sqlalchemy import func
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv()

APP_URL = os.getenv('APP_URL', 'http://localhost:8000')

def run_daily_agent():
    """Main agent job — runs every day at 8am"""
    print(f"🤖 Agent starting at {datetime.now(timezone.utc)}")
    
    from app.database import SessionLocal
    from app.models import Word, Video, QuizSession
    from app.services.youtube import build_youtube_client, build_gmail_client, get_todays_videos, get_transcript
    from app.services.vocab import extract_vocabulary, get_known_words
    from app.services.quiz import create_quiz_session, get_current_streak
    from app.services.email import send_quiz_email

    db = SessionLocal()

    today = datetime.now(timezone.utc).date()
    existing_session = db.query(QuizSession).filter(
        func.date(QuizSession.session_date) == today
    ).first()

    if existing_session:
        print(f"Session already exists for today: {existing_session.id}")
        db.close()
        return
    
    try:
        # Step 1: Get today's videos
        youtube = build_youtube_client()
        videos = get_todays_videos(youtube)
        
        new_words = []
        
        if videos:
            print(f"Found {len(videos)} new videos today")
            known_words = get_known_words(db, Word)
            
            for video in videos:
                # Skip already processed videos
                existing = db.query(Video).filter(
                    Video.video_id == video['video_id']
                ).first()
                if existing:
                    print(f"Already processed: {video['title']}")
                    continue
                
                # Get transcript
                transcript = get_transcript(video['video_id'])
                if not transcript:
                    print(f"No transcript for: {video['title']}")
                    continue
                
                # Extract new vocabulary
                print(f"Extracting vocabulary from: {video['title']}")
                words = extract_vocabulary(transcript, video['title'], known_words)
                
                # Save video to database
                db_video = Video(
                    video_id=video['video_id'],
                    title=video['title']
                )
                db.add(db_video)
                
                # Save new words to database
                for word_data in words:
                    existing_word = db.query(Word).filter(
                        Word.spanish == word_data['spanish']
                    ).first()
                    if not existing_word:
                        db_word = Word(
                            spanish=word_data['spanish'],
                            english=word_data['english'],
                            example_es=word_data['example_es'],
                            example_en=word_data['example_en'],
                            video_id=video['video_id']
                        )
                        db.add(db_word)
                        known_words.append(word_data['spanish'])
                        new_words.append(word_data)
                
                db.commit()
                print(f"Saved {len(words)} new words from {video['title']}")
        
        else:
            print("No new videos today — using review words only")
        
        # Step 2: Create quiz session
        session, all_words = create_quiz_session(db, new_words)
        
        if not all_words:
            print("No words to review today")
            return
        
        # Step 3: Get streak
        streak = get_current_streak(db)
        
        # Step 4: Send email
        gmail = build_gmail_client()
        send_quiz_email(gmail, session.id, len(all_words), APP_URL)
        
        print(f"✅ Agent done — {len(all_words)} words — streak: {streak}")
    
    except Exception as e:
        print(f"❌ Agent error: {e}")
        raise e
    
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_daily_agent,
        CronTrigger(hour=8, minute=0, timezone='Europe/Dublin')
    )
    scheduler.start()
    print("✅ Scheduler started — agent runs daily at 8am Dublin time")
    return scheduler