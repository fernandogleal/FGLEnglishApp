# GitHub Copilot Instructions for fglenglish

## Project Overview
This is a Flask-based English vocabulary learning application ("fglenglish") designed for pronunciation practice and shadowing. It uses the Oxford 3000/5000 word lists and integrates with Azure Cognitive Services for pronunciation assessment.

## Architecture & Core Components
- **Web Application**: Flask app located in `web_app/`.
  - Entry point: `web_app/app.py`.
  - Templates: `web_app/templates/` (Jinja2).
  - Static assets: `web_app/static/` (CSS, JS).
- **Database**: SQLite database at `masterfgl.db` (root directory).
  - Key tables: `oxford_words` (vocabulary, sentences, file paths), `pronunciation_reports` (Azure assessment results).
- **Data Storage**:
  - Native audios: `Oxford_list/audios/`.
  - User recordings: `Oxford_list/audios_user/`.
  - Generated reports: `output/`.

## Development Environment
- **Python Environment**: Conda environment named `audios`.
  - Always activate: `conda activate audios`.
- **Dependencies**: Listed in `requirements.txt`.
- **Configuration**: Environment variables are in `.env` (loaded via `python-dotenv`).

## Critical Workflows
### Running the Web App (Development)
The production app runs as a systemd service. To develop locally:
1. **Stop production service**: `sudo systemctl stop fglenglish` (frees port 5002).
2. **Run dev server**: `python web_app/app.py` (runs on port 5002 by default).
3. **Restart production**: `sudo systemctl start fglenglish` when finished.

### Azure Integration
- **Pronunciation Assessment**: Handled internally by `web_app/app.py` using Azure Speech SDK.
- **Credentials**: Ensure `FGL_SPEECH_SERVICE_KEY`, `FGL_SPEECH_REGION`, etc., are set in `.env`.

## Deployment Details
- **Service**: Systemd unit `fglenglish.service`.
- **Server**: Gunicorn serving the Flask app on `127.0.0.1:5002`.
- **Proxy**: Nginx configured as a reverse proxy (SSL/HTTPS enabled).
- **Logs**: `sudo journalctl -u fglenglish -f` (app), `/var/log/nginx/error.log` (web server).

## Conventions
- **Audio Files**: 
  - Naming: `[id]_[type]_[user].wav` (e.g., `0002_formal_user.wav`).
  - Format: 16kHz Mono WAV is required for Azure assessment (use `ensure_wav_16k_mono` helper).
- **Database Access**: The app connects to `masterfgl.db` from the root directory.
