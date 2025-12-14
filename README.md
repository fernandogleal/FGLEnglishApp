# English Flashcard App

A web-based flashcard application designed to help you study English vocabulary for a master's degree. The app focuses on the Oxford 3000/5000 word lists, providing example sentences, native audio pronunciations, and a feature to record and review your own pronunciation.

## Features

-   **Flashcard Interface**: Displays words with their part of speech, CEFR level, and example sentences (formal and informal).
-   **Shadowing Practice**: Practice pronunciation with longer texts from books.
    -   **Book & Chapter Selection**: Choose from available books and chapters.
    -   **Paragraph-based Learning**: Content is broken down into manageable chunks.
    -   **AI TTS Generation**: Generate high-quality Text-to-Speech audio for any paragraph using Azure AI.
    -   **Continuous Recording**: Record yourself reading the paragraph.
    -   **Instant Playback**: Listen to your recording immediately after finishing.
-   **Pronunciation Assessment**:
    -   **Detailed Scoring**: Get scores for Pronunciation, Accuracy, Fluency, and Prosody.
    -   **Total Score**: A comprehensive metric summing up all individual scores.
    -   **Feedback**: View recognized text and a list of mispronounced words with accuracy percentages.
-   **Audio Playback**: Listen to native audio (Flashcards) or AI-generated audio (Shadowing).
-   **Progress Tracking**:
    -   **Mark as Known**: Remove words from the study pool once mastered.
    -   **Repeat Later**: Keep words in the rotation for further practice.
-   **Level Filtering**: Study words based on their CEFR level (A1, A2, B1, B2, C1, etc.).

## Project Structure

```
fglenglish/
├── audios/
│   ├── audio_book_author/   # Original audiobook files
│   ├── audio_book_tts/      # Generated TTS audio files
│   └── audios_user/         # User-recorded audio files (Flashcard & Shadowing)
├── web_app/
│   ├── static/
│   │   ├── css/             # Stylesheets
│   │   └── js/              # Frontend logic (main.js, shadowing.js)
│   ├── templates/           # HTML templates (index.html, shadowing.html)
│   └── app.py               # Flask backend application
├── masterfgl.db             # SQLite database containing words, sentences, paragraphs, and reports
└── README.md                # Project documentation
```

## Setup & Installation

1.  **Prerequisites**:
    -   Python 3.x
    -   Conda (optional, but recommended)

2.  **Environment Setup**:
    If using Conda, create and activate the environment:
    ```bash
    conda create -n audios python=3.11
    conda activate audios
    conda install flask
    ```

3.  **Database**:
    The repository ships with the current `masterfgl.db` schema, including `audio_id` and `pronunciation_reports`. No migration scripts are required for normal use. If you bring an older DB, migrate it manually or restore from backup.

## Running the Application

1.  Navigate to the project root:
    ```bash
    cd /path/to/fglenglish
    ```

2.  Start the Flask server (use a different port if 5000 is already in use):
    ```bash
    # start from the audios conda env and override the port when needed
    FLASK_PORT=5001 conda run -n audios python web_app/app.py
    ```

3.  Open your web browser and go to:
    `http://127.0.0.1:5000`

## Deployment

The application is deployed on an Azure VM using Nginx and Gunicorn.

### Configuration Files
- **Systemd Service**: `/etc/systemd/system/fglenglish.service`
  - Manages the Gunicorn process on port 5002.
  - Uses the `audios` Conda environment.
- **Nginx Config**: `/etc/nginx/sites-available/fglenglish`
  - Reverse proxy to `127.0.0.1:5002`.
  - Serves static files and audio directories directly.
  - Enforces Basic Authentication (`/etc/apache2/.htpasswd`).
  - SSL/HTTPS configured via Certbot.

### Maintenance Commands
- **Restart App**: `sudo systemctl restart fglenglish`
- **Reload Nginx**: `sudo systemctl reload nginx`
- **Logs**:
  - App: `sudo journalctl -u fglenglish -f`
  - Nginx: `/var/log/nginx/error.log`

## Usage

### Flashcards
1.  **Select Level**: Choose your target CEFR level from the dropdown menu.
2.  **Study**:
    -   Read the word and sentences.
    -   Click **🔊 Listen** to hear the native pronunciation.
    -   Click **🎤 Record** to record your own voice.
    -   Click **▶️ My Rec** to listen to your recording.
    -   Click **⭐ Rate** to get AI feedback on your pronunciation.
3.  **Review**:
    -   Click **✅ Mark as Known** if you have mastered the word.
    -   Click **🔄 Repeat Later** to skip it for now and see it again later.

### Shadowing
1.  **Navigate**: Click "Shadowing" in the top navigation bar.
2.  **Select Content**: Choose a Book and Chapter.
3.  **Practice**:
    -   Listen to the **Original Audio** (if available) or **AI Generated TTS**.
    -   If TTS is missing, click **✨ Generate TTS Audio**.
    -   Click **🎤 Record** to read the paragraph aloud.
    -   Your recording will automatically appear in a player below the TTS.
    -   Click **⭐ Rate** to see your Total Score and mispronounced words.

## Database Schema (`masterfgl.db`)

The main table `oxford_words` contains:
-   `word`, `pos`, `level`: Core vocabulary data.
-   `sentence_formal`, `sentence_informal`: Example sentences.
-   `audio_formal_path`, `audio_informal_path`: Paths to native audio.
-   `user_audio_formal_path`, `user_audio_informal_path`: Paths to user recordings.
-   `is_known`: Boolean flag for progress tracking.
-   `id`: Numeric id matching the 4-digit audio filenames (e.g., 0002 → 2).

The table `paragraphs` contains content for Shadowing:
-   `id`: Unique identifier.
-   `book`, `chapter`, `subtitle`: Organization hierarchy.
-   `content`: The text content of the paragraph.
-   `audio_path`: Path to original audiobook file.
-   `tts_audio_path`: Path to generated TTS file.

The table `pronunciation_reports` stores pronunciation assessment outputs:
-   `audio_id`: Foreign key reference to the card id or paragraph id.
-   `pronunciation_score`, `accuracy_score`, `fluency_score`, `prosody_score`: Stored metrics.
-   `total_score`: Sum of the four metrics.
-   `recognized_text`: Full recognized text for the attempt.
-   `mispronunciations_json`, `prosody_issues_json`: Serialized details for UI/debugging.
-   `report_md_path`: Markdown report path generated by the assessment script.
-   `speech_type`: `formal` or `informal` (Flashcards).
-   `source`: `flashcard` or `shadowing`.

## License

Private project for personal study.


sudo systemctl stop fglenglish ## stop the program
python web_app/app.py          ## run the program in the foreground for debugging
sudo systemctl start fglenglish ## start the program again
