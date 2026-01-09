import sqlite3
import os

DB_PATH = 'masterfgl.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create user_words table
    print("Creating user_words table...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_words (
        username TEXT,
        word TEXT,
        pos TEXT,
        level TEXT,
        is_known INTEGER DEFAULT 0,
        user_audio_formal_path TEXT,
        user_audio_informal_path TEXT,
        user_transcription_formal TEXT,
        user_transcription_informal TEXT,
        PRIMARY KEY (username, word, pos, level)
    );
    """)
    
    # Add username to pronunciation_reports if not exists
    print("Checking pronunciation_reports schema...")
    cur.execute("PRAGMA table_info(pronunciation_reports)")
    columns = [info[1] for info in cur.fetchall()]
    if 'username' not in columns:
        print("Adding username column to pronunciation_reports...")
        cur.execute("ALTER TABLE pronunciation_reports ADD COLUMN username TEXT")
        
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
