import base64
import json
import mimetypes
import os
import pathlib
import random
import shutil
import sqlite3
import subprocess
import requests

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None
from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add project root to path to import scripts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from generate_shadowing_tts import generate_tts_for_audio_path, generate_tts_audio

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(BASE_DIR, 'masterfgl.db')
PITCH_DB_PATH = os.path.join(BASE_DIR, 'masterfgl.db')
AUDIO_DIR = os.path.join(BASE_DIR, 'audios')
AUDIO_BOOK_DIR = os.path.join(BASE_DIR, 'audios', 'audio_book_author')
AUDIO_BOOK_TTS_DIR = os.path.join(BASE_DIR, 'audios', 'audio_book_tts')
USER_AUDIO_DIR = os.path.join(BASE_DIR, 'audios', 'audios_user')
FFMPEG_BIN = shutil.which("ffmpeg")
SPEECH_KEY = os.environ.get("FGL_SPEECH_SERVICE_KEY")
SPEECH_REGION = os.environ.get("FGL_SPEECH_REGION", "eastus")

# Azure OpenAI Configuration
# Using Foundry endpoint/key from .env
AZURE_ENDPOINT = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
AZURE_API_KEY = os.environ.get("FOUNDRY_API_KEY")
AZURE_DEPLOYMENT = os.environ.get("FOUNDRY_MODEL_NAME", "gpt-4o-mini-transcribe")
AZURE_API_VERSION = "2024-02-15-preview"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pitch_db_connection():
    conn = sqlite3.connect(PITCH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def convert_to_wav_16k_mono(src_path, dest_path):
    if not FFMPEG_BIN:
        return False, "ffmpeg not found on server"

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i",
        src_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        dest_path,
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True, None
    except subprocess.CalledProcessError as exc:  # pragma: no cover - external tool
        err_text = exc.stderr.decode(errors="ignore") if exc.stderr else ""
        return False, err_text


import time
import threading

# ... existing imports ...

def run_pronunciation_assessment(file_path: str, reference_text: str):
    if not speechsdk:
        return None, "azure speech sdk not installed"
    if not SPEECH_KEY:
        return None, "FGL_SPEECH_SERVICE_KEY missing"

    speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)
    audio_config = speechsdk.audio.AudioConfig(filename=file_path)
    
    # Configure Pronunciation Assessment
    pa_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=True,
    )
    pa_config.enable_prosody_assessment()

    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language="en-US", audio_config=audio_config)
    pa_config.apply_to(recognizer)

    # Use continuous recognition to handle longer audio files
    done = False
    results = []
    
    def stop_cb(evt):
        nonlocal done
        done = True

    def recognized_cb(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            # Extract PA result for this segment
            pa_result = speechsdk.PronunciationAssessmentResult(evt.result)
            results.append({
                "text": evt.result.text,
                "pa_result": pa_result,
                "words": pa_result.words
            })

    recognizer.recognized.connect(recognized_cb)
    recognizer.session_stopped.connect(stop_cb)
    recognizer.canceled.connect(stop_cb)

    recognizer.start_continuous_recognition()

    # Wait for completion with a timeout (e.g., 5 minutes)
    start_time = time.time()
    while not done:
        time.sleep(0.1)
        if time.time() - start_time > 300:
            recognizer.stop_continuous_recognition()
            break
            
    recognizer.stop_continuous_recognition()

    if not results:
        return None, "No speech recognized"

    # Aggregate results
    total_words = 0
    weighted_pronunciation = 0.0
    weighted_accuracy = 0.0
    weighted_fluency = 0.0
    weighted_prosody = 0.0
    
    all_mis_words = []
    full_recognized_text = []

    for res in results:
        pa_res = res["pa_result"]
        words = res["words"] or []
        word_count = len(words)
        
        if word_count > 0:
            total_words += word_count
            weighted_pronunciation += pa_res.pronunciation_score * word_count
            weighted_accuracy += pa_res.accuracy_score * word_count
            weighted_fluency += pa_res.fluency_score * word_count
            weighted_prosody += pa_res.prosody_score * word_count
            
        full_recognized_text.append(res["text"])
        
        # Collect mispronunciations
        for w in words:
            err = getattr(w, "error_type", None)
            err_str = str(err) if err is not None else "None"
            if err_str == "Mispronunciation" or (hasattr(w, "accuracy_score") and w.accuracy_score < 60):
                all_mis_words.append({"word": w.word, "accuracy": w.accuracy_score, "error": err_str})

    if total_words == 0:
        # Fallback if no words detected but text exists?
        return None, "No words detected in speech"

    pronunciation_score = weighted_pronunciation / total_words
    accuracy_score = weighted_accuracy / total_words
    fluency_score = weighted_fluency / total_words
    prosody_score = weighted_prosody / total_words
    
    # Calculate total score (sum of all scores)
    total_score = pronunciation_score + accuracy_score + fluency_score + prosody_score

    final_scores = {
        "pronunciation_score": pronunciation_score,
        "accuracy_score": accuracy_score,
        "fluency_score": fluency_score,
        "prosody_score": prosody_score,
        "total_score": total_score,
        "recognized_text": " ".join(full_recognized_text),
        "mispronunciations": all_mis_words,
    }

    return final_scores, None

def transcribe_audio_file(file_path):
    if not AZURE_ENDPOINT or not AZURE_API_KEY:
        print("Azure credentials not found.")
        return None

    # Construct URL for Foundry/Azure OpenAI
    # Note: The endpoint structure might vary. 
    # If FOUNDRY_PROJECT_ENDPOINT is like ".../api/projects/...", we might need to adjust.
    # Standard Azure OpenAI format: {endpoint}/openai/deployments/{deployment}/audio/transcriptions?api-version={version}
    
    # Let's try to construct it based on the standard pattern first, assuming the endpoint provided is the base resource URL.
    # However, the user provided a specific FOUNDRY_PROJECT_ENDPOINT.
    # If it's a Foundry project endpoint, it might be different.
    # But usually for deployments it's: https://{resource}.openai.azure.com/openai/deployments/...
    
    # Let's try to parse the resource name from the endpoint if possible, or use it directly if it looks like a base URL.
    # The provided endpoint is: https://fleal-2555-resource.services.ai.azure.com/api/projects/fleal-2555
    # This looks like an AI Studio project endpoint.
    # The inference endpoint usually follows the standard Azure OpenAI pattern.
    
    # Let's try using the standard pattern with the resource name 'fleal-2555-resource' derived or hardcoded if needed.
    # Actually, let's try to use the endpoint provided by the user but strip the path if it's too specific, 
    # OR trust that the user provided the correct base for the OpenAI client.
    
    # Re-reading the error: "DeploymentNotFound". This means we hit the right server but wrong deployment name.
    # The user provided FOUNDRY_MODEL_NAME="gpt-4o-mini-transcribe".
    
    # Let's assume the base endpoint is https://fleal-2555-resource.cognitiveservices.azure.com/ (standard)
    # OR use the one provided.
    
    # Let's try to construct the URL carefully.
    # If AZURE_ENDPOINT is "https://fleal-2555-resource.services.ai.azure.com/api/projects/fleal-2555", 
    # that might be for management.
    
    # Let's try to use the standard cognitive services endpoint format if we can derive it, 
    # or use the one from the previous attempt which hit the server (404 on deployment).
    # The previous attempt used AZURE_TTS_ENDPOINT which was likely "https://fleal-2555-resource.cognitiveservices.azure.com/..."
    
    # Let's use the FOUNDRY_PROJECT_ENDPOINT as base, but we might need to adjust the path.
    # Actually, for "Foundry" / AI Studio, the endpoint for inference might be:
    # {endpoint}/deployments/{deployment_name}/audio/transcriptions?api-version={version}
    
    base_url = AZURE_ENDPOINT.rstrip('/')
    if "/openai/deployments" not in base_url:
         url = f"{base_url}/openai/deployments/{AZURE_DEPLOYMENT}/audio/transcriptions?api-version={AZURE_API_VERSION}"
    else:
         url = f"{base_url}/{AZURE_DEPLOYMENT}/audio/transcriptions?api-version={AZURE_API_VERSION}"

    headers = {
        "api-key": AZURE_API_KEY
    }
    
    mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, mime_type)}
            response = requests.post(url, headers=headers, files=files)
            
        if response.status_code == 200:
            return response.json().get('text')
        else:
            print(f"Transcription failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Transcription error: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/audios/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route('/audios_user/<path:filename>')
def serve_user_audio(filename):
    return send_from_directory(USER_AUDIO_DIR, filename)

@app.route('/audios_book/<path:filename>')
def serve_book_audio(filename):
    # Check if file exists in author directory
    if os.path.exists(os.path.join(AUDIO_BOOK_DIR, filename)):
        return send_from_directory(AUDIO_BOOK_DIR, filename)
    # Check if file exists in TTS directory
    if os.path.exists(os.path.join(AUDIO_BOOK_TTS_DIR, filename)):
        return send_from_directory(AUDIO_BOOK_TTS_DIR, filename)
    # Default to author directory (will 404 if not found)
    return send_from_directory(AUDIO_BOOK_DIR, filename)

@app.route('/shadowing')
def shadowing():
    return render_template('shadowing.html')

@app.route('/api/shadowing/books')
def get_shadowing_books():
    try:
        conn = get_pitch_db_connection()
        rows = conn.execute('SELECT DISTINCT book FROM paragraphs WHERE book IS NOT NULL ORDER BY book').fetchall()
        conn.close()
        return jsonify([row['book'] for row in rows])
    except Exception as e:
        print(f"Error in get_shadowing_books: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shadowing/structure')
def get_shadowing_structure():
    try:
        book = request.args.get('book')
        print(f"Fetching shadowing structure for book: {book}")
        
        conn = get_pitch_db_connection()
        
        query = 'SELECT DISTINCT chapter, subtitle FROM paragraphs WHERE 1=1'
        params = []
        
        if book:
            query += ' AND book = ?'
            params.append(book)
            
        query += ' ORDER BY id'
        
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        structure = {}
        for row in rows:
            chapter = row['chapter']
            subtitle = row['subtitle']
            
            if not chapter:
                continue
                
            if chapter not in structure:
                structure[chapter] = []
            
            if subtitle and subtitle not in structure[chapter]:
                structure[chapter].append(subtitle)
        
        print(f"Found {len(structure)} chapters.")
        return jsonify(structure)
    except Exception as e:
        print(f"Error in get_shadowing_structure: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shadowing/content')
def get_shadowing_content():
    try:
        book = request.args.get('book')
        chapter = request.args.get('chapter')
        subtitle = request.args.get('subtitle')
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        print(f"Fetching content for book: {book}, chapter: {chapter}, subtitle: {subtitle}")
        
        conn = get_pitch_db_connection()
        
        query = 'SELECT * FROM paragraphs WHERE 1=1'
        params = []
        
        if book:
            query += ' AND book = ?'
            params.append(book)
        
        if chapter:
            query += ' AND chapter = ?'
            params.append(chapter)
        
        if subtitle:
            query += ' AND subtitle = ?'
            params.append(subtitle)
            
        query += ' ORDER BY id LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        paragraphs = conn.execute(query, params).fetchall()
        conn.close()
        
        result = [dict(row) for row in paragraphs]
        print(f"Found {len(result)} paragraphs.")
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_shadowing_content: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shadowing/generate_tts', methods=['POST'])
def generate_shadowing_tts():
    data = request.json
    # We now expect 'id' (paragraph id) instead of 'audio_path'
    # But to support legacy or if UI sends audio_path, we handle both?
    # The user asked to "generate tts audio when the user click in the button".
    # If we changed the UI to be per-paragraph, we should expect 'id'.
    # If the UI is still per-group, we might have issues.
    # Let's assume we will update the UI to send 'id'.
    
    paragraph_id = data.get('id')
    
    if not paragraph_id:
        return jsonify({'error': 'Missing paragraph id'}), 400
        
    conn = get_pitch_db_connection()
    
    # Get the specific paragraph
    paragraph = conn.execute(
        'SELECT * FROM paragraphs WHERE id = ?',
        (paragraph_id,)
    ).fetchone()
    
    if not paragraph:
        conn.close()
        return jsonify({'error': 'Paragraph not found'}), 404
        
    content = paragraph['content']
    
    if not content or not content.strip():
        conn.close()
        return jsonify({'error': 'Empty text'}), 400
        
    # Determine output path
    # We can use the ID in the filename to be unique
    # e.g. "chunk_{id}_tts.mp3"
    
    try:
        new_filename = f"chunk_{paragraph_id}_tts.mp3"
        
        # Save to AUDIO_BOOK_TTS_DIR
        abs_output_path = os.path.join(AUDIO_BOOK_TTS_DIR, new_filename)
        
        # DB path should be relative
        db_path = f"audios/audio_book_tts/{new_filename}"
        
        # We need to import generate_tts_audio or use the one in app.py
        # It is defined in app.py
        
        success, err = generate_tts_audio(content, abs_output_path)
        
        if success:
            conn.execute(
                "UPDATE paragraphs SET tts_audio_path = ? WHERE id = ?",
                (db_path, paragraph_id)
            )
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'tts_path': db_path})
        else:
            conn.close()
            return jsonify({'error': f'TTS generation failed: {err}'}), 500
            
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/levels')
def get_levels():
    conn = get_db_connection()
    levels = conn.execute('SELECT DISTINCT level FROM oxford_words WHERE level IS NOT NULL ORDER BY level').fetchall()
    conn.close()
    return jsonify([row['level'] for row in levels])

@app.route('/api/card')
def get_card():
    level = request.args.get('level')
    conn = get_db_connection()
    
    query = "SELECT * FROM oxford_words WHERE is_known = 0 AND (audio_formal_path IS NOT NULL OR audio_informal_path IS NOT NULL) AND ((sentence_formal IS NOT NULL AND sentence_formal != '') OR (sentence_informal IS NOT NULL AND sentence_informal != ''))"
    params = []
    
    if level and level != 'all':
        query += " AND level = ?"
        params.append(level)
    
    # Get a random card
    # Note: For large DBs, ORDER BY RANDOM() can be slow, but for this size it's fine.
    query += " ORDER BY RANDOM() LIMIT 1"
    
    card = conn.execute(query, params).fetchone()
    conn.close()
    
    if card:
        return jsonify(dict(card))
    else:
        return jsonify({'error': 'No cards found'}), 404

@app.route('/api/mark_known', methods=['POST'])
def mark_known():
    data = request.json
    word = data.get('word')
    pos = data.get('pos')
    level = data.get('level')
    
    if not word:
        return jsonify({'error': 'Missing word'}), 400
        
    conn = get_db_connection()
    conn.execute(
        "UPDATE oxford_words SET is_known = 1 WHERE word = ? AND pos = ? AND level = ?",
        (word, pos, level)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/upload_audio', methods=['POST'])
def upload_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
        
    file = request.files['audio']
    source = request.form.get('source')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if source == 'shadowing':
        sentence_id = request.form.get('id')
        if not sentence_id:
             return jsonify({'error': 'Missing sentence ID'}), 400
        
        temp_filename = secure_filename(f"shadowing_{sentence_id}_user.webm")
        temp_path = os.path.join(USER_AUDIO_DIR, temp_filename)
        file.save(temp_path)
        
        final_filename = secure_filename(f"shadowing_{sentence_id}_user.wav")
        final_path = os.path.join(USER_AUDIO_DIR, final_filename)
        converted, err = convert_to_wav_16k_mono(temp_path, final_path)
        
        if converted:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            stored_filename = final_filename
        else:
            stored_filename = temp_filename
            
        # Update DB with user audio path
        try:
            conn = get_pitch_db_connection()
            # Store relative path consistent with other audio paths
            db_path = f"audios/audios_user/{stored_filename}"
            conn.execute(
                "UPDATE paragraphs SET user_audio_path = ? WHERE id = ?",
                (db_path, sentence_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating user audio path in DB: {e}")
            
        return jsonify({'success': True, 'path': stored_filename, 'converted': converted, 'error': err})

    word = request.form.get('word')
    pos = request.form.get('pos')
    level = request.form.get('level')
        
    if file and word:
        audio_type = request.form.get('type', 'formal') # 'formal' or 'informal'
        
        # Get existing audio path to derive ID
        conn = get_db_connection()
        row = conn.execute(
            "SELECT id AS audio_id, audio_formal_path, audio_informal_path FROM oxford_words WHERE word = ? AND pos = ? AND level = ?",
            (word, pos, level)
        ).fetchone()

        audio_id_val = None
        if row:
            audio_id_val = row["audio_id"]
            if audio_id_val is None:
                ref_path = row["audio_formal_path"] or row["audio_informal_path"]
                if ref_path:
                    basename = os.path.basename(ref_path)
                    audio_id_val = basename.split("_")[0]

        try:
            audio_id_str = f"{int(audio_id_val):04d}" if audio_id_val is not None else "unknown"
        except (TypeError, ValueError):
            audio_id_str = str(audio_id_val)

        # Save upload then normalize to WAV 16 kHz mono for downstream tools
        temp_filename = secure_filename(f"{audio_id_str}_{audio_type}_user.webm")
        temp_path = os.path.join(USER_AUDIO_DIR, temp_filename)
        file.save(temp_path)

        final_filename = secure_filename(f"{audio_id_str}_{audio_type}_user.wav")
        final_path = os.path.join(USER_AUDIO_DIR, final_filename)
        converted, err = convert_to_wav_16k_mono(temp_path, final_path)
        if converted:
            try:
                os.remove(temp_path)
            except OSError:
                pass
            stored_filename = final_filename
        else:
            # Fallback: keep original upload if ffmpeg unavailable
            stored_filename = temp_filename
        
        # Update DB
        column_to_update = 'user_audio_formal_path' if audio_type == 'formal' else 'user_audio_informal_path'

        conn.execute(
            f"UPDATE oxford_words SET {column_to_update} = ? WHERE word = ? AND pos = ? AND level = ?",
            (stored_filename, word, pos, level)
        )
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'path': stored_filename, 'converted': converted, 'error': err})
        
    return jsonify({'error': 'Upload failed'}), 500

@app.route('/api/transcribe', methods=['POST'])
def transcribe_endpoint():
    data = request.json
    word = data.get('word')
    pos = data.get('pos')
    level = data.get('level')
    audio_type = data.get('type') # 'formal' or 'informal'
    
    if not all([word, pos, level, audio_type]):
        return jsonify({'error': 'Missing parameters'}), 400
        
    conn = get_db_connection()
    
    # Get the user audio path
    column_to_select = 'user_audio_formal_path' if audio_type == 'formal' else 'user_audio_informal_path'
    row = conn.execute(
        f"SELECT {column_to_select} FROM oxford_words WHERE word = ? AND pos = ? AND level = ?",
        (word, pos, level)
    ).fetchone()
    
    if not row or not row[column_to_select]:
        conn.close()
        return jsonify({'error': 'No recording found to transcribe'}), 404
        
    filename = row[column_to_select]
    file_path = os.path.join(USER_AUDIO_DIR, filename)
    
    if not os.path.exists(file_path):
        conn.close()
        return jsonify({'error': 'Audio file missing on server'}), 404
        
    # Perform transcription
    transcription = transcribe_audio_file(file_path)
    
    if transcription:
        # Save to DB
        transcription_col = 'user_transcription_formal' if audio_type == 'formal' else 'user_transcription_informal'
        conn.execute(
            f"UPDATE oxford_words SET {transcription_col} = ? WHERE word = ? AND pos = ? AND level = ?",
            (transcription, word, pos, level)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'transcription': transcription})
    else:
        conn.close()
        return jsonify({'error': 'Transcription failed'}), 500


@app.route('/api/rate', methods=['POST'])
def rate_endpoint():
    if not speechsdk:
        return jsonify({'error': 'Azure Speech SDK not installed on server'}), 500

    data = request.json or {}
    
    if data.get('source') == 'shadowing':
        reference_text = data.get('reference_text')
        audio_path = data.get('audio_path')
        paragraph_id = data.get('id')
        
        if not reference_text or not audio_path:
            return jsonify({'error': 'Missing shadowing parameters'}), 400
            
        file_path = os.path.join(USER_AUDIO_DIR, audio_path)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Audio file missing on server'}), 404
            
        # Ensure WAV 16k mono
        temp_wav = os.path.join(USER_AUDIO_DIR, f"_rate_{audio_path}")
        converted, err = convert_to_wav_16k_mono(file_path, temp_wav)
        use_path = temp_wav if converted else file_path

        result, err = run_pronunciation_assessment(use_path, reference_text)

        if converted:
            try:
                os.remove(temp_wav)
            except OSError:
                pass

        if err:
            return jsonify({'error': err}), 500
            
        # Save to DB
        if paragraph_id:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO pronunciation_reports (
                        audio_id,
                        pronunciation_score,
                        accuracy_score,
                        fluency_score,
                        prosody_score,
                        total_score,
                        recognized_text,
                        mispronunciations_json,
                        prosody_issues_json,
                        report_md_path,
                        speech_type,
                        source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        paragraph_id,
                        result.get("pronunciation_score"),
                        result.get("accuracy_score"),
                        result.get("fluency_score"),
                        result.get("prosody_score"),
                        result.get("total_score"),
                        result.get("recognized_text"),
                        json.dumps(result.get("mispronunciations", [])),
                        json.dumps({}),
                        None,
                        'shadowing',
                        'shadowing'
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"Error saving shadowing report: {e}")

        return jsonify({'success': True, **result})

    word = data.get('word')
    pos = data.get('pos')
    level = data.get('level')
    audio_type = data.get('type')  # 'formal' or 'informal'

    if not all([word, pos, level, audio_type]):
        return jsonify({'error': 'Missing parameters'}), 400

    conn = get_db_connection()
    column_audio = 'user_audio_formal_path' if audio_type == 'formal' else 'user_audio_informal_path'
    column_sentence = 'sentence_formal' if audio_type == 'formal' else 'sentence_informal'

    row = conn.execute(
        f"SELECT id AS audio_id, {column_audio}, {column_sentence} FROM oxford_words WHERE word = ? AND pos = ? AND level = ?",
        (word, pos, level)
    ).fetchone()

    if not row or not row[column_audio]:
        conn.close()
        return jsonify({'error': 'No recording found to rate'}), 404

    sentence = row[column_sentence] or ""
    audio_id_val = row["audio_id"] if row else None
    filename = row[column_audio]
    file_path = os.path.join(USER_AUDIO_DIR, filename)
    conn.close()

    if not os.path.exists(file_path):
        return jsonify({'error': 'Audio file missing on server'}), 404

    # Ensure WAV 16k mono for assessment
    temp_wav = os.path.join(USER_AUDIO_DIR, f"_rate_{filename}.wav")
    converted, err = convert_to_wav_16k_mono(file_path, temp_wav)
    use_path = temp_wav if converted else file_path

    result, err = run_pronunciation_assessment(use_path, sentence)

    if converted:
        try:
            os.remove(temp_wav)
        except OSError:
            pass

    if err:
        return jsonify({'error': err}), 500

    # Persist to pronunciation_reports
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO pronunciation_reports (
                audio_id,
                pronunciation_score,
                accuracy_score,
                fluency_score,
                prosody_score,
                total_score,
                recognized_text,
                mispronunciations_json,
                prosody_issues_json,
                report_md_path,
                speech_type,
                source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audio_id_val,
                result.get("pronunciation_score"),
                result.get("accuracy_score"),
                result.get("fluency_score"),
                result.get("prosody_score"),
                result.get("total_score"),
                result.get("recognized_text"),
                json.dumps(result.get("mispronunciations", [])),
                json.dumps({}),
                None,
                audio_type,
                'flashcard'
            ),
        )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return jsonify({'success': True, **result})

if __name__ == '__main__':
    port = int(os.environ.get("FLASK_PORT", 5002))
    app.run(host='0.0.0.0', debug=True, port=port)
