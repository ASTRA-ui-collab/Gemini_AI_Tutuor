import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
NOTES_DIR = DATA_DIR / "notes"
PROGRESS_FILE = DATA_DIR / "progress.json"

DEFAULT_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]


def parse_model_candidates() -> List[str]:
    models_from_list = os.getenv("GEMINI_MODELS", "").strip()
    if models_from_list:
        parsed = [m.strip() for m in models_from_list.split(",") if m.strip()]
        if parsed:
            return parsed

    single = os.getenv("GEMINI_MODEL", "").strip()
    if single:
        return [single]

    return DEFAULT_MODELS[:]


API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
MODEL_CANDIDATES = parse_model_candidates()

NOTES_DIR.mkdir(parents=True, exist_ok=True)
if not PROGRESS_FILE.exists():
    PROGRESS_FILE.write_text("{}", encoding="utf-8")


def normalize_topic(topic: str) -> str:
    return " ".join(topic.strip().split()).lower()


def load_progress() -> Dict[str, int]:
    try:
        raw = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except Exception:
        raw = {}

    cleaned: Dict[str, int] = {}
    for key, value in raw.items():
        topic_key = normalize_topic(str(key))
        if not topic_key:
            continue
        try:
            cleaned[topic_key] = cleaned.get(topic_key, 0) + int(value)
        except Exception:
            continue
    return cleaned


def save_progress(data: Dict[str, int]) -> None:
    PROGRESS_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")


def pick_mime_type(file_path: Union[Path, str]) -> str:
    ext = Path(file_path).suffix.lower()
    image_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    audio_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }
    return image_map.get(ext) or audio_map.get(ext) or "application/octet-stream"


def is_api_error_text(text: str) -> bool:
    return text.startswith("Gemini API Error:")


class SomaTutor:
    def __init__(self) -> None:
        if not API_KEY:
            raise ValueError("Missing GOOGLE_API_KEY in environment/.env")
        self.client = genai.Client(api_key=API_KEY)
        self.model_candidates = MODEL_CANDIDATES

    def _extract_text(self, response) -> str:
        if hasattr(response, "text") and response.text:
            return response.text
        try:
            return response.candidates[0].content.parts[0].text
        except Exception:
            return str(response)

    def _is_not_found(self, err: str) -> bool:
        lower = err.lower()
        return "404" in lower and ("not_found" in lower or "not found" in lower)

    def _classify_error(self, err: str) -> str:
        lower = err.lower()
        if self._is_not_found(err):
            return "NOT_FOUND"
        if "429" in lower or "resource_exhausted" in lower:
            return "QUOTA_EXHAUSTED"
        if "401" in lower or "unauthenticated" in lower or "invalid api key" in lower:
            return "AUTH"
        if "403" in lower or "permission_denied" in lower:
            return "PERMISSION"
        if "deadline_exceeded" in lower or "timed out" in lower or "timeout" in lower:
            return "TIMEOUT"
        return "ERROR"

    def generate(self, contents: Union[str, List[genai_types.Content]]) -> str:
        last_error = ""
        for model_name in self.model_candidates:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                )
                return self._extract_text(response)
            except Exception as exc:
                error_text = str(exc)
                last_error = f"{model_name}: {error_text}"
                if self._is_not_found(error_text):
                    continue
                return f"Gemini API Error: {error_text}"
        return f"Gemini API Error: all candidate models failed. Last error: {last_error}"

    def check_access(self) -> str:
        lines = ["Gemini access check", "-" * 40]
        statuses: Dict[str, int] = {
            "OK": 0,
            "NOT_FOUND": 0,
            "QUOTA_EXHAUSTED": 0,
            "AUTH": 0,
            "PERMISSION": 0,
            "TIMEOUT": 0,
            "ERROR": 0,
        }

        for model_name in self.model_candidates:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents="Reply with exactly: OK",
                )
                text = self._extract_text(response).strip()
                statuses["OK"] += 1
                lines.append(f"[OK] {model_name} -> {text[:120]}")
            except Exception as exc:
                error_text = str(exc)
                bucket = self._classify_error(error_text)
                statuses[bucket] += 1
                lines.append(f"[{bucket}] {model_name} -> {error_text[:180]}")

        lines.append("-" * 40)
        lines.append(
            "Summary: "
            + ", ".join(f"{k}={v}" for k, v in statuses.items() if v > 0)
        )

        if statuses["OK"] > 0:
            lines.append("Result: Gemini is reachable. At least one configured model works.")
        elif statuses["AUTH"] > 0:
            lines.append("Blocked by authentication. Check GOOGLE_API_KEY.")
        elif statuses["PERMISSION"] > 0:
            lines.append("Blocked by project/API permissions for this key.")
        elif statuses["QUOTA_EXHAUSTED"] > 0:
            lines.append("Blocked by quota/billing limits on this project.")
        elif statuses["NOT_FOUND"] == len(self.model_candidates):
            lines.append("Blocked by model names. None of the configured models are available.")
        else:
            lines.append("Blocked by API/network/runtime errors. See per-model details above.")

        return "\n".join(lines)

    def get_difficulty(self, topic: str) -> str:
        data = load_progress()
        score = data.get(normalize_topic(topic), 0)
        if score > 5:
            return "easy"
        if score > 2:
            return "medium"
        return "hard"

    def update_progress(self, topic: str) -> None:
        topic_key = normalize_topic(topic)
        if not topic_key:
            return
        data = load_progress()
        data[topic_key] = data.get(topic_key, 0) + 1
        save_progress(data)

    def ask(self, topic: str, question: str) -> str:
        difficulty = self.get_difficulty(topic)
        prompt = f"""
You are Soma AI, an adaptive learning tutor.

Difficulty level: {difficulty}
Topic: {topic}

Explain clearly step-by-step.
Use examples.
Adjust depth based on difficulty.

Question:
{question}
""".strip()
        return self.generate(prompt)

    def summarize(self, text: str) -> str:
        prompt = f"""
Convert this into structured bullet notes.
Highlight key ideas, definitions, and examples.

Text:
{text}
""".strip()
        return self.generate(prompt)

    def generate_quiz(self, topic: str) -> str:
        prompt = f"""
Create 5 university-level quiz questions.
Provide answers at the end.

Topic: {topic}
""".strip()
        return self.generate(prompt)

    def _analyze_bytes(self, file_bytes: bytes, mime_type: str, prompt: str) -> str:
        file_part = genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        text_part = genai_types.Part.from_text(text=prompt)
        contents = [genai_types.Content(role="user", parts=[file_part, text_part])]
        return self.generate(contents)

    def analyze_image_bytes(self, image_bytes: bytes, mime_type: str) -> str:
        prompt = (
            "Analyze this photo in detail. Describe visible objects, setting, actions, "
            "text in image, and notable visual cues. Then provide a structured summary."
        )
        return self._analyze_bytes(image_bytes, mime_type, prompt)

    def transcribe_audio_bytes(self, audio_bytes: bytes, mime_type: str) -> str:
        prompt = (
            "Transcribe this lecture audio faithfully. Then provide:\n"
            "1) clean transcript,\n"
            "2) key points,\n"
            "3) short revision summary,\n"
            "4) 5 quiz questions."
        )
        return self._analyze_bytes(audio_bytes, mime_type, prompt)

    def analyze_image(self, image_path: str) -> str:
        clean_path = image_path.strip()
        if not clean_path:
            return "No image selected."
        path = Path(clean_path)
        if not path.exists():
            return "Image file not found."
        if not path.is_file():
            return "Provided path is not a file."
        try:
            data = path.read_bytes()
        except PermissionError:
            return "Permission denied while reading image."
        except Exception as exc:
            return f"Could not read image: {exc}"
        return self.analyze_image_bytes(data, pick_mime_type(path))

    def transcribe_audio(self, audio_path: str) -> str:
        clean_path = audio_path.strip()
        if not clean_path:
            return "No audio selected."
        path = Path(clean_path)
        if not path.exists():
            return "Audio file not found."
        if not path.is_file():
            return "Provided path is not a file."
        try:
            data = path.read_bytes()
        except PermissionError:
            return "Permission denied while reading audio."
        except Exception as exc:
            return f"Could not read audio: {exc}"
        return self.transcribe_audio_bytes(data, pick_mime_type(path))

    def save_note(self, text: str) -> Path:
        filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S.txt")
        path = NOTES_DIR / filename
        path.write_text(text, encoding="utf-8")
        return path

    def run_and_track(self, topic: str, fn) -> Tuple[str, Optional[Path]]:
        result = fn()
        if is_api_error_text(result):
            return result, None
        self.update_progress(topic)
        note = self.save_note(result)
        return result, note
