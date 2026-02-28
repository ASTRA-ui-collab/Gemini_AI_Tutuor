# Soma AI Tutor (CLI + Flask Web App)

## Features
- Ask Tutor
- Summarize Text
- Generate Quiz
- Analyze Image (Multimodal)
- Check Gemini Access
- Transcribe Lecture Audio (inside Multimodal)

## Setup
1. Create your local env file from the template:
   - Copy `soma_ai_tutor/.env.example` to `soma_ai_tutor/.env`
   - Set `GOOGLE_API_KEY` to your own key
   - Optional: edit `GEMINI_MODELS=gemini-2.5-flash-lite,gemini-2.0-flash-lite,gemini-2.0-flash`
2. Install dependencies:
   - `pip install -r requirements.txt`

## Run CLI
- `cd soma_ai_tutor`
- `python soma.py`

## Run Web App
- `python -m soma_ai_tutor.web_app`
- Open `http://127.0.0.1:5000`

## Deploy
This repo includes:
- `requirements.txt`
- `Procfile`
- `runtime.txt`

Example (Render/Heroku style):
- Build: `pip install -r requirements.txt`
- Start: `gunicorn soma_ai_tutor.web_app:app`
