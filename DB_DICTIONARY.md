# Database Dictionary: masterfgl.db

This document describes the schema of the SQLite database `masterfgl.db` used in the FGL English application.

## Tables Overview

| Table Name | Description |
| :--- | :--- |
| `oxford_words` | Main vocabulary table containing words, definitions, sentences, and audio paths. |
| `pronunciation_reports` | Stores results from Azure pronunciation assessment for user recordings. |
| `paragraphs` | Stores content for the shadowing feature (book chapters and subtitles). |
| `sentences` | Stores individual sentences extracted from the source material. |
| `word_frequency` | Tracks word frequency statistics. |
| `known_words` | Simple list of words marked as known (legacy or auxiliary). |
| `sqlite_sequence` | Internal SQLite table for tracking auto-increment sequences. |

---

## Table Details

### 1. `oxford_words`
The core table for the flashcard application.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `word` | `TEXT` | The vocabulary word (part of Primary Key). |
| `pos` | `TEXT` | Part of speech (e.g., noun, verb) (part of Primary Key). |
| `level` | `TEXT` | CEFR level (e.g., a1, b2) (part of Primary Key). |
| `original_list` | `TEXT` | Source list name (e.g., Oxford 3000). |
| `page_col` | `TEXT` | Reference to page/column in original PDF/source. |
| `sentence_formal` | `TEXT` | Example sentence in a formal context. |
| `sentence_informal` | `TEXT` | Example sentence in an informal context. |
| `sentence_formal_prosody` | `TEXT` | Prosody markup/guide for the formal sentence. |
| `sentence_informal_prosody` | `TEXT` | Prosody markup/guide for the informal sentence. |
| `audio_formal_path` | `TEXT` | Filename of the native formal audio (in `audios/audios_tts_sentences`). |
| `audio_informal_path` | `TEXT` | Filename of the native informal audio (in `audios/audios_tts_sentences`). |
| `user_audio_formal_path` | `TEXT` | Filename of the user's recorded formal audio (in `audios/audios_user`). |
| `user_audio_informal_path` | `TEXT` | Filename of the user's recorded informal audio (in `audios/audios_user`). |
| `user_transcription_formal` | `TEXT` | STT transcription of the user's formal recording. |
| `user_transcription_informal` | `TEXT` | STT transcription of the user's informal recording. |
| `is_known` | `INTEGER` | Status flag: `0` = learning, `1` = known/mastered. Default `0`. |

**Primary Key**: (`word`, `pos`, `level`)

---

### 2. `pronunciation_reports`
Stores detailed feedback from the Azure Speech Assessment API.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key (Auto-increment). |
| `audio_id` | `INTEGER` | Reference ID linking to the word/audio being assessed. |
| `created_at` | `TEXT` | Timestamp of report creation (Default: `CURRENT_TIMESTAMP`). |
| `pronunciation_score` | `REAL` | Overall pronunciation score (0-100). |
| `accuracy_score` | `REAL` | Accuracy score (0-100). |
| `fluency_score` | `REAL` | Fluency score (0-100). |
| `prosody_score` | `REAL` | Prosody score (0-100). |
| `recognized_text` | `TEXT` | The text recognized by the speech engine. |
| `mispronunciations_json` | `TEXT` | JSON string containing details of mispronounced words. |
| `prosody_issues_json` | `TEXT` | JSON string containing details of prosody issues. |
| `report_md_path` | `TEXT` | Path to a generated Markdown report file (optional). |
| `speech_type` | `TEXT` | Type of speech assessed (e.g., 'formal', 'informal'). |

**Indexes**:
*   `idx_pronunciation_reports_audio_id` on `audio_id`

---

### 3. `paragraphs`
Used for the "Shadowing" feature, organizing content by chapters.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INT` | Unique identifier for the paragraph. |
| `chapter` | `TEXT` | Chapter name or number. |
| `subtitle` | `TEXT` | Subtitle or section within the chapter. |
| `content` | `TEXT` | The text content of the paragraph. |
| `file_source` | `TEXT` | Source filename of the text. |
| `word_count` | `INT` | Number of words in the paragraph. |
| `audio_path` | `TEXT` | Filename of the original audiobook audio (in `audios/audio_book_author`). |
| `tts_audio_path` | `TEXT` | Filename of the generated TTS audio (in `audios/audio_book_tts`). |

---

### 4. `sentences`
Auxiliary table for sentence-level analysis.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INT` | Unique identifier. |
| `sentence` | `TEXT` | The sentence text. |
| `file_source` | `TEXT` | Source file. |
| `chapter` | `TEXT` | Chapter context. |
| `subtitle` | `TEXT` | Subtitle context. |

---

### 5. `word_frequency`
Statistical data on word usage.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `word` | `TEXT` | The word. |
| `frequency` | `INT` | Count of occurrences. |
| `length` | `INT` | Character length of the word. |
| `is_known` | `INT` | Flag indicating if the word is known. |

---

### 6. `known_words`
Simple list of known words.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `word` | `TEXT` | The known word. |

---

### 7. `sqlite_sequence`
Internal SQLite table.

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `name` | | Table name. |
| `seq` | | Current sequence number. |
