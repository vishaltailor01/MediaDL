import os
import urllib.request
from pathlib import Path

from .analyzer import analyze_document
from .exporter import export_course_package
from .markdown_parser import parse_markdown
from .planner import build_course_package
from .schemas import CoursePlanRequest, CoursePlanResponse

# Custom exception for empty script segments
class EmptyScriptException(Exception):
    pass

_kokoro_model = None

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"


def _ensure_kokoro_files() -> tuple[str, str]:
    """
    Ensures that Kokoro-ONNX model files are cached in the user's home directory.
    """
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "kokoro-onnx")
    os.makedirs(cache_dir, exist_ok=True)
    
    model_path = os.path.join(cache_dir, "kokoro-v1.0.onnx")
    voices_path = os.path.join(cache_dir, "voices-v1.0.bin")
    
    if not os.path.exists(model_path):
        print(f"Downloading Kokoro ONNX model from {MODEL_URL} to {model_path}...")
        urllib.request.urlretrieve(MODEL_URL, model_path)
        
    if not os.path.exists(voices_path):
        print(f"Downloading Kokoro voices binary from {VOICES_URL} to {voices_path}...")
        urllib.request.urlretrieve(VOICES_URL, voices_path)
        
    return model_path, voices_path


def synthesize_narration(text: str, temp_dir: str) -> str:
    """
    Synthesizes narration speech using Kokoro-ONNX.
    Handles text length limitations by splitting long text into smaller sentences,
    synthesizing each sentence, and concatenating the audio.
    Saves the output as a local temporary .wav file.
    """
    if not text.strip():
        raise EmptyScriptException("Narration script text is empty.")
        
    global _kokoro_model
    if _kokoro_model is None:
        from kokoro_onnx import Kokoro
        model_path, voices_path = _ensure_kokoro_files()
        _kokoro_model = Kokoro(model_path, voices_path)
        
    import uuid
    import soundfile as sf
    import numpy as np
    import re

    # Helper to split text into chunks (sentences/phrases) within ~250 characters
    def split_text_to_chunks(input_text: str, max_chars: int = 250) -> list[str]:
        # Split by periods, question marks, exclamation marks, or newlines
        sentences = re.split(r'(?<=[.?!])\s+|\n+', input_text)
        
        chunks = []
        current_chunk = []
        current_len = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(sentence) > max_chars:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                    
                # Split long sentence by clauses (commas)
                sub_sentences = re.split(r'(?<=,)\s+', sentence)
                for sub_s in sub_sentences:
                    if len(sub_s) > max_chars:
                        # Split by space
                        words = sub_s.split(" ")
                        temp_w = []
                        temp_len = 0
                        for w in words:
                            if temp_len + len(w) + 1 > max_chars:
                                chunks.append(" ".join(temp_w))
                                temp_w = [w]
                                temp_len = len(w)
                            else:
                                temp_w.append(w)
                                temp_len += len(w) + 1
                        if temp_w:
                            chunks.append(" ".join(temp_w))
                    else:
                        chunks.append(sub_s)
            else:
                if current_len + len(sentence) + 1 > max_chars:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [sentence]
                    current_len = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_len += len(sentence) + 1
                    
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return [c.strip() for c in chunks if c.strip()]

    chunks = split_text_to_chunks(text)
    all_samples = []
    sample_rate = 24000
    
    for chunk in chunks:
        samples, sr = _kokoro_model.create(
            chunk,
            voice="af_sarah",
            speed=1.0,
            lang="en-us"
        )
        sample_rate = sr
        all_samples.append(samples)
        # Add a short 0.25 second silence between chunks for natural cadence
        silence = np.zeros(int(sample_rate * 0.25), dtype=np.float32)
        all_samples.append(silence)
        
    if all_samples:
        all_samples.pop()  # Remove the trailing silence
        final_samples = np.concatenate(all_samples)
    else:
        final_samples = np.zeros(0, dtype=np.float32)
        
    out_wav_path = os.path.join(temp_dir, f"narration_{uuid.uuid4().hex}.wav")
    sf.write(out_wav_path, final_samples, sample_rate)
    return out_wav_path



async def render_slide_playwright(title: str, code_snippet: str, output_path: str) -> None:
    """
    Generates a premium dark layout slide frame using Playwright headless Chromium.
    """
    from playwright.async_api import async_playwright
    import pygments
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import HtmlFormatter
    
    code_html = ""
    if code_snippet.strip():
        try:
            lexer = get_lexer_by_name("python")
        except Exception:
            from pygments.lexers import TextLexer
            lexer = TextLexer()
        formatter = HtmlFormatter(style="monokai", noclasses=True)
        code_html = pygments.highlight(code_snippet, lexer, formatter)
        
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono&display=swap');
            body {{
                margin: 0;
                padding: 0;
                width: 1920px;
                height: 1080px;
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Inter', sans-serif;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                box-sizing: border-box;
                border: 2px solid #30363d;
            }}
            .container {{
                width: 90%;
                max-width: 1600px;
                display: flex;
                flex-direction: column;
                gap: 40px;
            }}
            .title {{
                font-size: 64px;
                font-weight: 800;
                color: #ffffff;
                margin: 0;
                line-height: 1.2;
                background: linear-gradient(90deg, #58a6ff, #bc8cff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .code-wrapper {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 12px;
                padding: 30px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 28px;
                line-height: 1.5;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }}
            pre {{
                margin: 0 !important;
                white-space: pre-wrap;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="title">{title}</h1>
            {f'<div class="code-wrapper">{code_html}</div>' if code_html else ''}
        </div>
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.set_content(html_content)
        await page.wait_for_timeout(500)
        await page.screenshot(path=output_path)
        await browser.close()


def render_slide_pillow(title: str, code_snippet: str, output_path: str) -> None:
    """
    Pillow slide rendering fallback.
    """
    from PIL import Image, ImageDraw, ImageFont
    
    img = Image.new("RGB", (1920, 1080), color=(13, 17, 23))
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype("arial.ttf", 64)
        code_font = ImageFont.truetype("consolas.ttf", 28)
    except IOError:
        title_font = ImageFont.load_default()
        code_font = ImageFont.load_default()
        
    draw.text((100, 100), title, font=title_font, fill=(88, 166, 255))
    
    if code_snippet.strip():
        draw.rectangle([100, 250, 1820, 980], fill=(22, 27, 34), outline=(48, 54, 61), width=2)
        lines = code_snippet.splitlines()
        y = 280
        for line in lines[:22]:
            draw.text((130, y), line, font=code_font, fill=(201, 209, 217))
            y += 30
            
    img.save(output_path)


async def generate_slide_image(title: str, code_snippet: str, output_path: str) -> None:
    """
    Generates a high-resolution slide PNG image for a segment, trying Playwright first with a Pillow fallback.
    """
    try:
        await render_slide_playwright(title, code_snippet, output_path)
    except Exception as exc:
        print(f"Playwright slide generation failed ({exc}), falling back to Pillow.")
        render_slide_pillow(title, code_snippet, output_path)


def create_course_plan(request: CoursePlanRequest) -> CoursePlanResponse:
    document = parse_markdown(request.markdown)
    analysis = analyze_document(document, request.audience_level)
    course = build_course_package(
        document=document,
        analysis=analysis,
        target=request.target,
        transformation_mode=request.transformation_mode,
        course_goal=request.course_goal,
    )
    return CoursePlanResponse(analysis=analysis, course=course)


def create_course_export(request: CoursePlanRequest, output_root: str | Path):
    response = create_course_plan(request)
    return export_course_package(response.course, output_root)
