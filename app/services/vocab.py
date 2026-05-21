import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

claude = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def extract_vocabulary(transcript: str, video_title: str, known_words: list) -> list:
    """
    Extract new vocabulary words from transcript
    that the user hasn't seen before
    """
    
    known_words_str = ', '.join(known_words) if known_words else 'none yet'
    
    prompt = f"""
    You are a Spanish teacher helping a complete beginner (A1 level).
    
    From this Spanish transcript, extract vocabulary words suitable for a beginner.
    
    IMPORTANT RULES:
    - Skip these already known words: {known_words_str}
    - Only include common, useful everyday words
    - Skip proper nouns, names, places
    - Aim for 10-20 new words depending on content
    - If a word is a variation of a known word, skip it
    
    Return ONLY valid JSON, no markdown, no explanation:
    {{
        "words": [
            {{
                "spanish": "trabajar",
                "english": "to work",
                "example_es": "Me gusta trabajar desde casa.",
                "example_en": "I like to work from home."
            }}
        ]
    }}
    
    Transcript: {transcript}
    """
    
    response = claude.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': prompt}]
    )
    
    text = response.content[0].text.strip()
    
    # Clean markdown if present
    if '```' in text:
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
        text = text.split('```')[0]
    
    data = json.loads(text.strip())
    return data['words']


def get_known_words(db, Word) -> list:
    """Get all Spanish words already in database"""
    words = db.query(Word.spanish).all()
    return [w.spanish for w in words]