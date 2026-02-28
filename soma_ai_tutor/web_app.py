import os

from flask import Flask, redirect, render_template, request, url_for

try:
    from core import MODEL_CANDIDATES, SomaTutor, is_api_error_text, pick_mime_type
except ImportError:
    from .core import MODEL_CANDIDATES, SomaTutor, is_api_error_text, pick_mime_type

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.secret_key = os.getenv("FLASK_SECRET_KEY", "soma-dev-secret")

tutor = SomaTutor()


@app.route("/")
def index():
    return redirect(url_for("ask_tutor"))


@app.route("/ask", methods=["GET", "POST"])
def ask_tutor():
    result = ""
    error = ""
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        question = request.form.get("question", "").strip()
        if not topic or not question:
            error = "Topic and question are required."
        else:
            result = tutor.ask(topic, question)
            if not is_api_error_text(result):
                tutor.update_progress(topic)
            else:
                error = "Gemini request failed. Progress was not updated."
    return render_template(
        "page.html",
        active="ask",
        title="Ask Tutor",
        result=result,
        error=error,
        model_candidates=MODEL_CANDIDATES,
    )


@app.route("/summarize", methods=["GET", "POST"])
def summarize():
    result = ""
    error = ""
    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if not text:
            error = "Text is required."
        else:
            result = tutor.summarize(text)
    return render_template(
        "page.html",
        active="summarize",
        title="Summarize Text",
        result=result,
        error=error,
        model_candidates=MODEL_CANDIDATES,
    )


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    result = ""
    error = ""
    if request.method == "POST":
        topic = request.form.get("topic", "").strip()
        if not topic:
            error = "Topic is required."
        else:
            result = tutor.generate_quiz(topic)
    return render_template(
        "page.html",
        active="quiz",
        title="Generate Quiz",
        result=result,
        error=error,
        model_candidates=MODEL_CANDIDATES,
    )


@app.route("/multimodal", methods=["GET", "POST"])
def multimodal():
    result = ""
    error = ""
    mode = request.form.get("mode", "image")
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename:
            error = "Please upload a file."
        else:
            file_bytes = upload.read()
            mime_type = upload.mimetype or pick_mime_type(upload.filename)
            if mode == "audio":
                result = tutor.transcribe_audio_bytes(file_bytes, mime_type)
            else:
                result = tutor.analyze_image_bytes(file_bytes, mime_type)
    return render_template(
        "page.html",
        active="multimodal",
        title="Analyze Image / Transcribe Audio",
        result=result,
        error=error,
        mode=mode,
        model_candidates=MODEL_CANDIDATES,
    )


@app.route("/access", methods=["GET"])
def check_access():
    result = tutor.check_access()
    return render_template(
        "page.html",
        active="access",
        title="Check Gemini Access",
        result=result,
        error="",
        model_candidates=MODEL_CANDIDATES,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
