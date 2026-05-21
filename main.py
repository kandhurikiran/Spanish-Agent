import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.database import engine, get_db, Base
from app.models import Word, QuizSession, WordResult
from app.services.quiz import (
    get_session_words,
    save_word_result,
    complete_session,
    get_current_streak
)
from app.scheduler import start_scheduler, run_daily_agent

load_dotenv()

templates = Jinja2Templates(directory="templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all database tables on startup
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    scheduler = start_scheduler()
    # Start the scheduler
    print("✅ Scheduler started")
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(title="Spanish Learning Agent", lifespan=lifespan)

# ── Request Models ────────────────────────────────────────────────────────
class AnswerRequest(BaseModel):
    session_id: int
    word_id: int
    correct: bool

class CompleteRequest(BaseModel):
    session_id: int

# ── Routes ────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    total_words = db.query(Word).count()
    total_sessions = db.query(QuizSession).filter(
        QuizSession.completed == True
    ).count()
    streak = get_current_streak(db)
    
    content = f"""<!DOCTYPE html>
<html>
<body style="background:#11111b;color:#cdd6f4;font-family:Arial;padding:40px;text-align:center;">
    <h1 style="color:#cba6f7;">Spanish Agent</h1>
    <p>Total words learned: <strong style="color:#a6e3a1;">{total_words}</strong></p>
    <p>Quizzes completed: <strong style="color:#a6e3a1;">{total_sessions}</strong></p>
    <p>Current streak: <strong style="color:#fab387;">{streak}</strong></p>
    <br>
    <a href="/run-agent" style="background:#cba6f7;color:#11111b;padding:12px 30px;
       border-radius:8px;text-decoration:none;font-weight:bold;">Run Agent Now</a>
</body>
</html>"""
    return HTMLResponse(content=content)

@app.get("/quiz/{session_id}", response_class=HTMLResponse)
async def quiz_page(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db)
):
    """Serve the quiz page"""
    session = db.query(QuizSession).filter(
        QuizSession.id == session_id
    ).first()
    
    if not session:
        return HTMLResponse(content="Quiz not found", status_code=404)
    
    words = get_session_words(db, session_id)
    print(f"Words found: {len(words)}")  # add this
    print(f"First word: {words[0] if words else 'NONE'}")  # add this
    streak = get_current_streak(db)
    
    words_data = [
        {
            "id": w.id,
            "spanish": w.spanish,
            "english": w.english,
            "example_es": w.example_es,
            "example_en": w.example_en
        }
        for w in words
    ]
    
    return templates.TemplateResponse(
    request=request,
    name="quiz.html",
    context={
        "words": words_data,
        "session_id": session_id,
        "total_words": len(words_data),
        "streak": streak,
        "session": session
    })

@app.post("/quiz/answer")
async def submit_answer(
    answer: AnswerRequest,
    db: Session = Depends(get_db)
):
    """Save word result and update spaced repetition"""
    session = save_word_result(
        db,
        answer.session_id,
        answer.word_id,
        answer.correct
    )
    return {
        "correct": session.correct_words,
        "total": session.total_words
    }

@app.post("/quiz/complete")
async def complete_quiz(
    data: CompleteRequest,
    db: Session = Depends(get_db)
):
    """Mark quiz as completed"""
    streak = get_current_streak(db)
    session = complete_session(db, data.session_id, streak)
    return {"streak": streak, "score": session.correct_words}

@app.get("/run-agent")
async def run_agent_now():
    """Manually trigger the agent — useful for testing"""
    try:
        run_daily_agent()
        return {"status": "success", "message": "Agent ran successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)