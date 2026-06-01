import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from course_generator.schemas import CoursePlanRequest
from course_generator.markdown_parser import parse_markdown
from course_generator.analyzer import analyze_document
from course_generator.planner import build_course_package
from course_generator.exporter import export_course_package
from course_generator.service import create_course_plan


def test_course_plan_request_defaults_to_original_both_beginner():
    request = CoursePlanRequest(markdown="# Demo\n\nContent")

    assert request.target == "both"
    assert request.audience_level == "beginner"
    assert request.transformation_mode == "original"
    assert request.course_goal == "Create a practical course from this Markdown source."


def test_parse_markdown_extracts_title_sections_timestamps_links_and_code():
    markdown = """# Demo Course

Intro text.

## 00:00 Setup

Visit https://example.com.

```python
print("hello")
```

## Next Steps

More content.
"""

    document = parse_markdown(markdown)

    assert document.title == "Demo Course"
    assert len(document.sections) == 2
    assert document.sections[0].heading == "00:00 Setup"
    assert document.sections[0].timestamps == ["00:00"]
    assert document.sections[0].links == ["https://example.com"]
    assert document.sections[0].code_blocks == ['print("hello")']


def test_analyze_document_detects_transcript_from_timestamps():
    document = parse_markdown(
        "# Video\n\n## Transcript\n\n00:00 Intro\n01:30 Demo\n02:00 Wrap up"
    )

    analysis = analyze_document(document, audience_level="intermediate")

    assert analysis.source_type == "transcript"
    assert analysis.audience_level == "intermediate"
    assert analysis.recommended_lesson_count >= 1
    assert analysis.segmentation_strategy == "timestamps"


def test_analyze_document_detects_documentation_from_code_blocks():
    document = parse_markdown(
        "# API Guide\n\n## Install\n\n```python\nprint('x')\n```\n\n"
        "## Usage\n\n```python\nprint('y')\n```"
    )

    analysis = analyze_document(document, audience_level="beginner")

    assert analysis.source_type in ("documentation", "tutorial")
    assert analysis.segmentation_strategy == "headings"


def test_build_course_package_creates_modules_lessons_and_video_assets():
    document = parse_markdown(
        "# AI Notes\n\n## Agents\n\nAgents use tools.\n\n## RAG\n\nRAG retrieves context."
    )
    analysis = analyze_document(document, audience_level="beginner")

    course = build_course_package(
        document=document,
        analysis=analysis,
        target="both",
        transformation_mode="original",
        course_goal="Create a practical course.",
    )

    assert course.title == "AI Notes"
    assert course.target == "both"
    assert course.transformation_mode == "original"
    assert course.modules
    assert course.modules[0].lessons
    lesson = course.modules[0].lessons[0]
    assert lesson.slide_outline.startswith("# Slide Outline")
    assert lesson.video_script.startswith("# Video Script")
    assert lesson.storyboard.startswith("# Storyboard")
    assert lesson.quiz[0].type == "multiple_choice"


def test_transcript_course_uses_timestamp_chapters_not_metadata_headings():
    document = parse_markdown(
        """# YouTube

## Complete Agentic AI Course

### Video Metadata
- **Runtime:** PT673M26S

### Description
Timestamp
00:00:00 Introduction
00:02:31 Langchain Course
02:35:12 RAG Course

### Transcript
Welcome to this practical agentic AI course. We will start with the overall
plan, then build LangChain examples, and later implement retrieval augmented
generation workflows with exercises and evaluation checkpoints.
"""
    )
    analysis = analyze_document(document, audience_level="beginner")

    course = build_course_package(
        document=document,
        analysis=analysis,
        target="both",
        transformation_mode="original",
        course_goal="Create a practical course.",
    )

    lessons = course.modules[0].lessons
    titles = [lesson.title for lesson in lessons]

    assert course.title == "Complete Agentic AI Course"
    assert titles == ["Introduction", "Langchain Course", "RAG Course"]
    assert "Video Metadata" not in titles
    assert "Description" not in titles
    assert "Transcript" not in titles
    assert "agentic AI course" in lessons[0].explanation
    assert lessons[0].explanation != (
        "This lesson introduces the core ideas and turns them into practical "
        "learning steps."
    )


def test_export_course_package_writes_markdown_json_and_zip(tmp_path):
    document = parse_markdown("# Demo\n\n## Intro\n\nContent")
    analysis = analyze_document(document)
    course = build_course_package(document, analysis, "both", "original", "Create a course.")

    package_dir, zip_path = export_course_package(course, tmp_path)

    assert (package_dir / "course-outline.md").exists()
    assert (package_dir / "course.json").exists()
    assert (package_dir / "lessons" / "lesson-01-01.md").exists()
    assert (package_dir / "slides" / "lesson-01-01-slides.md").exists()
    assert (package_dir / "scripts" / "lesson-01-01-video-script.md").exists()
    assert (package_dir / "storyboards" / "lesson-01-01-storyboard.md").exists()
    assert (package_dir / "web" / "web-course.json").exists()
    assert zip_path.exists()


def test_exported_lesson_contains_course_ready_assets(tmp_path):
    document = parse_markdown("# Demo\n\n## Intro\n\nContent for the lesson.")
    analysis = analyze_document(document)
    course = build_course_package(document, analysis, "both", "original", "Create a course.")

    package_dir, _ = export_course_package(course, tmp_path)
    lesson_markdown = (package_dir / "lessons" / "lesson-01-01.md").read_text(
        encoding="utf-8"
    )

    assert "## Teaching Flow" in lesson_markdown
    assert "## Slide Outline" in lesson_markdown
    assert "## Video Script" in lesson_markdown
    assert "## Storyboard" in lesson_markdown
    assert "**Answer:**" in lesson_markdown


def test_create_course_plan_orchestrates_parser_analyzer_and_planner():
    response = create_course_plan(
        CoursePlanRequest(
            markdown="# Demo\n\n## Intro\n\nContent",
            target="web",
            audience_level="advanced",
            transformation_mode="instructional",
        )
    )

    assert response.analysis.audience_level == "advanced"
    assert response.course.target == "web"
    assert response.course.transformation_mode == "instructional"
    assert response.course.modules[0].lessons[0].title == "Intro"
