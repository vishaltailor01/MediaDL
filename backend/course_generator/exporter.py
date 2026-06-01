import json
import shutil
from pathlib import Path
from uuid import uuid4

from .schemas import CoursePackage


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _course_outline(course: CoursePackage) -> str:
    modules = "\n".join(f"- {module.title}" for module in course.modules)
    outcomes = "\n".join(f"- {outcome}" for outcome in course.learning_outcomes)
    return f"""# {course.title}

## Description
{course.description}

## Audience Level
{course.audience_level}

## Learning Outcomes
{outcomes}

## Modules
{modules}

## Final Project
{course.final_project}
"""


def _lesson_markdown(course_title: str, module_title: str, lesson) -> str:
    objectives = "\n".join(f"- {objective}" for objective in lesson.learning_objectives)
    quiz = "\n\n".join(
        (
            f"### Question {index}\n"
            f"{question.question}\n\n"
            + "\n".join(f"- {choice}" for choice in question.choices)
            + f"\n\n**Answer:** {question.answer}\n\n"
            f"**Explanation:** {question.explanation}"
        )
        for index, question in enumerate(lesson.quiz, start=1)
    )
    return f"""# {lesson.title}

Course: {course_title}
Module: {module_title}

## Learning Objectives
{objectives}

## Explanation
{lesson.explanation}

## Teaching Flow
1. Introduce the lesson goal and connect it to the course outcome.
2. Explain the core idea using the lesson explanation above.
3. Demonstrate the idea with a concrete example or short walkthrough.
4. Let learners complete the exercise and compare their output against the goal.
5. Check understanding with the quiz before moving to the next lesson.

## Exercise
{lesson.exercise}

## Quiz
{quiz}

## Slide Outline
{lesson.slide_outline}

## Video Script
{lesson.video_script}

## Storyboard
{lesson.storyboard}
"""


def export_course_package(
    course: CoursePackage, output_root: str | Path
) -> tuple[Path, Path]:
    output_root = Path(output_root)
    package_dir = output_root / f"course-package-{uuid4()}"
    package_dir.mkdir(parents=True, exist_ok=True)

    _write(package_dir / "course-outline.md", _course_outline(course))
    _write(package_dir / "course.json", course.model_dump_json(indent=2))
    _write(package_dir / "web" / "web-course.json", course.model_dump_json(indent=2))

    quiz_questions = []
    exercises = []
    youtube_lines = [f"# YouTube Playlist Plan: {course.title}", ""]

    for module in course.modules:
        _write(
            package_dir / "modules" / f"{module.id}.md",
            f"# {module.title}\n\n{module.description}\n",
        )
        youtube_lines.append(f"## {module.title}")
        for lesson in module.lessons:
            _write(
                package_dir / "lessons" / f"{lesson.id}.md",
                _lesson_markdown(course.title, module.title, lesson),
            )
            _write(package_dir / "slides" / f"{lesson.id}-slides.md", lesson.slide_outline)
            _write(
                package_dir / "scripts" / f"{lesson.id}-video-script.md",
                lesson.video_script,
            )
            _write(
                package_dir / "storyboards" / f"{lesson.id}-storyboard.md",
                lesson.storyboard,
            )
            quiz_questions.extend(question.model_dump() for question in lesson.quiz)
            exercises.append(f"## {lesson.title}\n\n{lesson.exercise}\n")
            youtube_lines.append(f"- {lesson.title}")

    _write(
        package_dir / "quizzes" / "quiz-bank.json",
        json.dumps({"questions": quiz_questions}, indent=2),
    )
    _write(package_dir / "exercises" / "exercises.md", "\n".join(exercises))
    _write(package_dir / "youtube" / "playlist-plan.md", "\n".join(youtube_lines) + "\n")
    _write(
        package_dir / "youtube" / "lesson-metadata.md",
        "# Lesson Metadata\n\nAdd titles, descriptions, and chapters per lesson.\n",
    )

    zip_file = shutil.make_archive(str(package_dir), "zip", package_dir)
    return package_dir, Path(zip_file)


def transcribe_audio_to_srt(audio_path: str, srt_path: str) -> None:
    """
    Integrates faster-whisper to transcribe the master audio track and output a time-synced SRT file.
    Performs regex technical vocabulary corrections (e.g. LLM, RAG, LangChain).
    """
    from faster_whisper import WhisperModel
    import re
    
    # Load WhisperModel (tiny model size on CPU using int8 quantization)
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(audio_path, beam_size=5)
    
    def correct_vocab(text: str) -> str:
        corrections = {
            r"\blang[\s_-]?chain\b": "LangChain",
            r"\brag\b": "RAG",
            r"\bllm\b": "LLM",
            r"\bllms\b": "LLMs",
            r"\bonnx\b": "ONNX",
            r"\bffmpeg\b": "FFmpeg",
            r"\bfastapi\b": "FastAPI",
            r"\bmarkdown\b": "Markdown",
            r"\bpython\b": "Python",
            r"\bmistune\b": "Mistune",
            r"\bmoviepy\b": "MoviePy",
            r"\bplaywright\b": "Playwright",
            r"\bwhisper\b": "Whisper",
            r"\bkokoro\b": "Kokoro",
            r"\bagentic\b": "Agentic",
        }
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def format_ts(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
    with open(srt_path, "w", encoding="utf-8") as f:
        for index, segment in enumerate(segments, start=1):
            start_str = format_ts(segment.start)
            end_str = format_ts(segment.end)
            text = correct_vocab(segment.text.strip())
            f.write(f"{index}\n")
            f.write(f"{start_str} --> {end_str}\n")
            f.write(f"{text}\n\n")

