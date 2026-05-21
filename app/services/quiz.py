from datetime import datetime, timezone
from app.models import Word, QuizSession, WordResult
from app.services.srs import calculate_next_review, get_words_due_today

def create_quiz_session(db, new_words: list) -> QuizSession:
    """Create a new quiz session combining new words and words due for review"""
    
    # Get words due for review today
    review_words = get_words_due_today(db, Word)
    
    # Combine new words + review words (avoid duplicates)
    review_spanish = [w.spanish for w in review_words]
    new_word_objects = db.query(Word).filter(
        Word.spanish.in_([w['spanish'] for w in new_words])
    ).all()
    
    # Merge — review words first, then new words
    all_words = review_words + [
        w for w in new_word_objects 
        if w.spanish not in review_spanish
    ]
    
    # Create quiz session
    session = QuizSession(
        total_words=len(all_words),
        correct_words=0,
        completed=False
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session, all_words


def save_word_result(db, session_id: int, word_id: int, correct: bool):
    # Check if already answered
    existing = db.query(WordResult).filter(
        WordResult.session_id == session_id,
        WordResult.word_id == word_id
    ).first()
    
    if existing:
        return db.query(QuizSession).filter(
            QuizSession.id == session_id
        ).first()
    
    # Save result
    result = WordResult(
        session_id=session_id,
        word_id=word_id,
        correct=correct
    )
    db.add(result)
    
    # Update spaced repetition
    word = db.query(Word).filter(Word.id == word_id).first()
    word = calculate_next_review(word, correct)
    
    # Update session score
    session = db.query(QuizSession).filter(
        QuizSession.id == session_id
    ).first()
    if correct:
        session.correct_words += 1
    
    db.commit()
    return session


def complete_session(db, session_id: int, streak_day: int):
    """Mark quiz session as completed"""
    session = db.query(QuizSession).filter(QuizSession.id == session_id).first()
    session.completed = True
    session.streak_day = streak_day
    db.commit()
    return session


def get_session_words(db, session_id: int):
    """Get all words for a quiz session"""
    results = db.query(WordResult).filter(
        WordResult.session_id == session_id
    ).all()
    
    word_ids = [r.word_id for r in results] if results else []
    
    if not word_ids:
        # New session — get all words from session
        session = db.query(QuizSession).filter(
            QuizSession.id == session_id
        ).first()
        return db.query(Word).limit(session.total_words).all()
    
    return db.query(Word).filter(Word.id.in_(word_ids)).all()


def get_current_streak(db):
    """Calculate current streak days"""
    sessions = db.query(QuizSession).filter(
        QuizSession.completed == True
    ).order_by(QuizSession.session_date.desc()).all()
    
    if not sessions:
        return 0
    
    streak = 0
    today = datetime.now(timezone.utc).date()
    
    for session in sessions:
        session_date = session.session_date.date()
        expected_date = today - __import__('datetime').timedelta(days=streak)
        
        if session_date == expected_date:
            streak += 1
        else:
            break
    
    return streak