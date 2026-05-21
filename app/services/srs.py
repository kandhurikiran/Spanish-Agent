from datetime import datetime, timedelta

def calculate_next_review(word, correct: bool):
    """
    SM-2 Spaced Repetition Algorithm
    
    correct = True  → word interval increases (seen less often)
    correct = False → word resets (seen tomorrow again)
    """
    
    if correct:
        if word.repetitions == 0:
            word.interval = 1
        elif word.repetitions == 1:
            word.interval = 3
        else:
            word.interval = round(word.interval * word.ease_factor)
        
        word.repetitions += 1
        
        # Increase ease factor for correct answers (max 2.5)
        word.ease_factor = min(2.5, word.ease_factor + 0.1)
    
    else:
        # Wrong answer — reset to tomorrow
        word.interval = 1
        word.repetitions = 0
        
        # Decrease ease factor for wrong answers (min 1.3)
        word.ease_factor = max(1.3, word.ease_factor - 0.2)
    
    # Set next review date
    word.next_review = datetime.utcnow() + timedelta(days=word.interval)
    
    return word


def get_words_due_today(db, Word):
    """Get all words that are due for review today"""
    now = datetime.utcnow()
    return db.query(Word).filter(Word.next_review <= now).all()


def get_new_words(db, Word, known_spanish_words: list):
    """Get words not yet seen"""
    return db.query(Word).filter(
        Word.spanish.notin_(known_spanish_words)
    ).all()