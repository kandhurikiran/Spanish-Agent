from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class Video(Base):
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True)
    video_id = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    processed_at = Column(DateTime, server_default=func.now())

class Word(Base):
    __tablename__ = "words"
    
    id = Column(Integer, primary_key=True)
    spanish = Column(String, unique=True, nullable=False)
    english = Column(String, nullable=False)
    example_es = Column(Text, nullable=False)
    example_en = Column(Text, nullable=False)
    video_id = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Spaced repetition fields
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    next_review = Column(DateTime, server_default=func.now())

class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    
    id = Column(Integer, primary_key=True)
    session_date = Column(DateTime, server_default=func.now())
    total_words = Column(Integer, default=0)
    correct_words = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    streak_day = Column(Integer, default=0)

class WordResult(Base):
    __tablename__ = "word_results"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=False)
    word_id = Column(Integer, nullable=False)
    correct = Column(Boolean, nullable=False)
    answered_at = Column(DateTime, server_default=func.now())