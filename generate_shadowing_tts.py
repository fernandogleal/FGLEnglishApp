#!/usr/bin/env python3
import sqlite3
import os
import pathlib
import requests
import json
import base64
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv(pathlib.Path(__file__).parent / ".env")

PROJECT_ROOT = pathlib.Path(__file__).parent
DB_PATH = PROJECT_ROOT / "masterfgl.db"
AUDIO_OUTPUT_DIR = PROJECT_ROOT / "audios" / "audio_book_tts"

def decode_audio(response: requests.Response) -> bytes:
    content_type = response.headers.get("Content-Type", "").lower()
    if "application/json" in content_type:
        payload = response.json()
        audio = payload.get("audio") or payload.get("data")
        if not audio:
            raise ValueError("JSON response did not include an 'audio' field")
        return base64.b64decode(audio)
    return response.content

def send_request(text: str, voice: str = "alloy", speed: float = 1.0) -> requests.Response:
    endpoint = os.environ.get("AZURE_TTS_ENDPOINT")
    if not endpoint:
        endpoint = "https://fleal-2555-resource.cognitiveservices.azure.com/openai/deployments/gpt-4o-mini-tts/audio/speech?api-version=2024-02-15-preview"

    api_key = os.environ.get("AZURE_TTS_KEY") or os.environ.get("FOUNDRY_API_KEY")
         
    if not api_key:
        raise RuntimeError("Missing API key (AZURE_TTS_KEY or FOUNDRY_API_KEY)")

    payload = {
        "voice": voice,
        "response_format": "mp3",
        "speed": speed,
        "model": "gpt-4o-mini-tts",
        "input": text,
    }

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }

    response = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=120)
    if response.status_code != 200:
        print(f"TTS Error {response.status_code}: {response.text}")
    return response

def generate_tts_audio(text: str, output_path: str):
    """
    Generates TTS for the given text and saves it to output_path.
    Returns (success, error_message).
    """
    try:
        output_file = pathlib.Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        response = send_request(text)
        response.raise_for_status()
        audio_data = decode_audio(response)
        
        output_file.write_bytes(audio_data)
        return True, None
    except Exception as e:
        print(f"Error generating TTS: {e}")
        return False, str(e)

def generate_tts_for_audio_path(audio_path: str):
    """
    Generates TTS for a specific audio_path (group of paragraphs).
    Updates the database with the new TTS path.
    Returns (success, message/path).
    """
    if not DB_PATH.exists():
        return False, f"Database not found at {DB_PATH}"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Fetch text
        cursor.execute("SELECT content FROM paragraphs WHERE audio_path = ? ORDER BY id", (audio_path,))
        paragraphs = cursor.fetchall()
        
        if not paragraphs:
            return False, "No paragraphs found for this audio path"

        full_text = " ".join([p['content'] for p in paragraphs])
        
        if not full_text.strip():
            return False, "Empty text content"
            
        # Prepare filename
        # audio_path example: "audios/audio_book_author/001chapter_01.mp3"
        original_path = pathlib.Path(audio_path)
        new_filename = f"{original_path.stem}_tts.mp3"
        output_file = AUDIO_OUTPUT_DIR / new_filename
        
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Generating TTS for {new_filename}...")
        
        response = send_request(full_text)
        response.raise_for_status()
        audio_data = decode_audio(response)
        
        output_file.write_bytes(audio_data)
        
        # Update DB
        # Store relative path: "audios/audio_book_tts/filename"
        db_path = f"audios/audio_book_tts/{new_filename}"
        
        cursor.execute(
            "UPDATE paragraphs SET tts_audio_path = ? WHERE audio_path = ?", 
            (db_path, audio_path)
        )
        conn.commit()
        
        return True, db_path

    except Exception as e:
        print(f"Error generating TTS: {e}")
        return False, str(e)
    finally:
        conn.close()

def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Ensure column exists
    try:
        cursor.execute("ALTER TABLE paragraphs ADD COLUMN tts_audio_path TEXT")
        print("Added tts_audio_path column to paragraphs table.")
    except sqlite3.OperationalError:
        pass # Column likely exists

    # Get groups
    cursor.execute("SELECT DISTINCT audio_path FROM paragraphs WHERE audio_path IS NOT NULL")
    groups = cursor.fetchall()
    
    print(f"Found {len(groups)} audio groups.")
    conn.close()

    for row in groups:
        audio_path = row['audio_path']
        success, result = generate_tts_for_audio_path(audio_path)
        if success:
            print(f"  Success: {result}")
        else:
            print(f"  Failed: {result}")

if __name__ == "__main__":
    main()
