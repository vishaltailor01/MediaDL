# Generic Markdown Course Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a generic Markdown-to-course asset generator that accepts any `.md` content and produces a structured course package for YouTube and web-app delivery.

**Architecture:** Add a new `backend/course_generator/` package that is independent from the existing downloader/transcript code. The package parses Markdown, analyzes content shape, creates a course blueprint, generates lesson/presentation/video assets, and exports Markdown/JSON files. FastAPI endpoints in `backend/main.py` will expose planning and export workflows.

**Tech Stack:** Python, FastAPI, Pydantic, pytest, zipfile, standard-library Markdown heuristics for v1.

---

## File Structure

- Create `backend/course_generator/__init__.py`: package marker and public exports.
- Create `backend/course_generator/schemas.py`: Pydantic models for requests, analysis, courses, assets, and exports.
- Create `backend/course_generator/markdown_parser.py`: parse generic Markdown into structured sections.
- Create `backend/course_generator/analyzer.py`: classify source type, topic hints, level, and segmentation strategy.
- Create `backend/course_generator/planner.py`: build course outline, modules, lessons, quizzes, slides, scripts, and storyboards.
- Create `backend/course_generator/exporter.py`: write asset package files and zip them.
- Create `backend/course_generator/service.py`: orchestration functions used by API routes.
- Modify `backend/main.py`: add `/course/plan`, `/course/export`, and `/course/download/{package_id}` endpoints.
- Modify `backend/test_main.py`: add API-level tests.
- Create `backend/test_course_generator.py`: unit tests for parser, analyzer, planner, exporter, and service.
- Create `docs/course-generator/README.md`: project documentation. This already exists and should be updated as implementation details evolve.

## Data Model

Use these core concepts:

```python
SourceType = Literal[
    "transcript",
    "article",
    "documentation",
    "tutorial",
    "lecture_notes",
    "meeting_notes",
    "research_notes",
    "unknown",
]

TargetType = Literal["youtube", "web", "both"]
AudienceLevel = Literal["beginner", "intermediate", "advanced"]
TransformationMode = Literal["extractive", "instructional", "original"]
```

## Implementation Tasks

### Task 1: Add Schemas

**Files:**
- Create: `backend/course_generator/__init__.py`
- Create: `backend/course_generator/schemas.py`
- Test: `backend/test_course_generator.py`

- [ ] **Step 1: Write failing schema tests**

Create `backend/test_course_generator.py`:

```python
from course_generator.schemas import CoursePlanRequest


def test_course_plan_request_defaults_to_original_both_beginner():
    request = CoursePlanRequest(markdown="# Demo\n\nContent")

    assert request.target == "both"
    assert request.audience_level == "beginner"
    assert request.transformation_mode == "original"
    assert request.course_goal == "Create a practical course from this Markdown source."
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_course_plan_request_defaults_to_original_both_beginner -v
```

Expected: failure because `course_generator.schemas` does not exist.

- [ ] **Step 3: Create package marker**

Create `backend/course_generator/__init__.py`:

```python
"""Generic Markdown-to-course asset generation."""
```

- [ ] **Step 4: Implement schemas**

Create `backend/course_generator/schemas.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal[
    "transcript",
    "article",
    "documentation",
    "tutorial",
    "lecture_notes",
    "meeting_notes",
    "research_notes",
    "unknown",
]
TargetType = Literal["youtube", "web", "both"]
AudienceLevel = Literal["beginner", "intermediate", "advanced"]
TransformationMode = Literal["extractive", "instructional", "original"]


class CoursePlanRequest(BaseModel):
    markdown: str = Field(min_length=1)
    target: TargetType = "both"
    audience_level: AudienceLevel = "beginner"
    transformation_mode: TransformationMode = "original"
    course_goal: str = "Create a practical course from this Markdown source."


class MarkdownSection(BaseModel):
    level: int
    heading: str
    content: str
    timestamps: list[str] = []
    code_blocks: list[str] = []
    links: list[str] = []


class MarkdownDocument(BaseModel):
    title: str
    raw_markdown: str
    sections: list[MarkdownSection]


class ContentAnalysis(BaseModel):
    source_type: SourceType
    topic: str
    audience_level: AudienceLevel
    recommended_lesson_count: int
    segmentation_strategy: str


class QuizQuestion(BaseModel):
    id: str
    type: Literal["multiple_choice"]
    question: str
    choices: list[str]
    answer: str
    explanation: str


class LessonAsset(BaseModel):
    id: str
    title: str
    learning_objectives: list[str]
    explanation: str
    exercise: str
    quiz: list[QuizQuestion]
    slide_outline: str
    video_script: str
    storyboard: str


class ModuleAsset(BaseModel):
    id: str
    title: str
    description: str
    lessons: list[LessonAsset]


class CoursePackage(BaseModel):
    schema_version: str = "1.0"
    title: str
    description: str
    target: TargetType
    audience_level: AudienceLevel
    transformation_mode: TransformationMode
    learning_outcomes: list[str]
    prerequisites: list[str]
    modules: list[ModuleAsset]
    final_project: str


class CoursePlanResponse(BaseModel):
    analysis: ContentAnalysis
    course: CoursePackage


class CourseExportResponse(BaseModel):
    package_id: str
    download_url: str
```

- [ ] **Step 5: Run schema test**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_course_plan_request_defaults_to_original_both_beginner -v
```

Expected: pass.

### Task 2: Parse Generic Markdown

**Files:**
- Modify: `backend/course_generator/markdown_parser.py`
- Test: `backend/test_course_generator.py`

- [ ] **Step 1: Add failing parser tests**

Append to `backend/test_course_generator.py`:

```python
from course_generator.markdown_parser import parse_markdown


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
```

- [ ] **Step 2: Run parser test to verify it fails**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_parse_markdown_extracts_title_sections_timestamps_links_and_code -v
```

Expected: failure because `markdown_parser.py` does not exist.

- [ ] **Step 3: Implement parser**

Create `backend/course_generator/markdown_parser.py`:

```python
import re

from .schemas import MarkdownDocument, MarkdownSection

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
TIMESTAMP_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
LINK_RE = re.compile(r"https?://[^\s)>\"]+")
CODE_BLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```", re.DOTALL)


def _extract_code_blocks(text: str) -> list[str]:
    return [match.strip() for match in CODE_BLOCK_RE.findall(text)]


def _strip_code_blocks(text: str) -> str:
    return CODE_BLOCK_RE.sub("", text)


def parse_markdown(markdown: str) -> MarkdownDocument:
    matches = list(HEADING_RE.finditer(markdown))
    title = "Untitled Course"
    sections: list[MarkdownSection] = []

    if matches and matches[0].group(1) == "#":
        title = matches[0].group(2).strip()

    content_matches = matches[1:] if matches and matches[0].group(1) == "#" else matches
    for index, match in enumerate(content_matches):
        start = match.end()
        end = content_matches[index + 1].start() if index + 1 < len(content_matches) else len(markdown)
        section_content = markdown[start:end].strip()
        searchable_content = _strip_code_blocks(section_content)
        sections.append(
            MarkdownSection(
                level=len(match.group(1)),
                heading=match.group(2).strip(),
                content=section_content,
                timestamps=TIMESTAMP_RE.findall(match.group(2) + "\n" + searchable_content),
                code_blocks=_extract_code_blocks(section_content),
                links=LINK_RE.findall(searchable_content),
            )
        )

    if not sections and markdown.strip():
        searchable_content = _strip_code_blocks(markdown)
        sections.append(
            MarkdownSection(
                level=1,
                heading=title,
                content=markdown.strip(),
                timestamps=TIMESTAMP_RE.findall(searchable_content),
                code_blocks=_extract_code_blocks(markdown),
                links=LINK_RE.findall(searchable_content),
            )
        )

    return MarkdownDocument(title=title, raw_markdown=markdown, sections=sections)
```

- [ ] **Step 4: Run parser test**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_parse_markdown_extracts_title_sections_timestamps_links_and_code -v
```

Expected: pass.

### Task 3: Analyze Content Shape

**Files:**
- Create: `backend/course_generator/analyzer.py`
- Test: `backend/test_course_generator.py`

- [ ] **Step 1: Add failing analyzer tests**

Append:

```python
from course_generator.analyzer import analyze_document


def test_analyze_document_detects_transcript_from_timestamps():
    document = parse_markdown("# Video\n\n## Transcript\n\n00:00 Intro\n01:30 Demo\n02:00 Wrap up")

    analysis = analyze_document(document, audience_level="intermediate")

    assert analysis.source_type == "transcript"
    assert analysis.audience_level == "intermediate"
    assert analysis.recommended_lesson_count >= 1
    assert analysis.segmentation_strategy == "timestamps"


def test_analyze_document_detects_documentation_from_code_blocks():
    document = parse_markdown("# API Guide\n\n## Install\n\n```python\nprint('x')\n```\n\n## Usage\n\n```python\nprint('y')\n```")

    analysis = analyze_document(document, audience_level="beginner")

    assert analysis.source_type in ("documentation", "tutorial")
    assert analysis.segmentation_strategy == "headings"
```

- [ ] **Step 2: Run analyzer tests to verify they fail**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_analyze_document_detects_transcript_from_timestamps backend/test_course_generator.py::test_analyze_document_detects_documentation_from_code_blocks -v
```

Expected: failure because `analyzer.py` does not exist.

- [ ] **Step 3: Implement analyzer**

Create `backend/course_generator/analyzer.py`:

```python
from .schemas import AudienceLevel, ContentAnalysis, MarkdownDocument, SourceType


def _classify_source(document: MarkdownDocument) -> SourceType:
    timestamp_count = sum(len(section.timestamps) for section in document.sections)
    code_count = sum(len(section.code_blocks) for section in document.sections)
    heading_count = len(document.sections)
    raw_lower = document.raw_markdown.lower()

    if timestamp_count >= 2 or "transcript" in raw_lower:
        return "transcript"
    if code_count >= 2 and heading_count >= 2:
        return "tutorial"
    if code_count >= 1 and ("api" in raw_lower or "install" in raw_lower or "usage" in raw_lower):
        return "documentation"
    if heading_count >= 3:
        return "article"
    return "unknown"


def analyze_document(
    document: MarkdownDocument,
    audience_level: AudienceLevel = "beginner",
) -> ContentAnalysis:
    source_type = _classify_source(document)
    timestamp_count = sum(len(section.timestamps) for section in document.sections)
    segmentation_strategy = "timestamps" if source_type == "transcript" and timestamp_count else "headings"
    recommended_lesson_count = max(1, min(24, len(document.sections)))

    return ContentAnalysis(
        source_type=source_type,
        topic=document.title,
        audience_level=audience_level,
        recommended_lesson_count=recommended_lesson_count,
        segmentation_strategy=segmentation_strategy,
    )
```

- [ ] **Step 4: Run analyzer tests**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_analyze_document_detects_transcript_from_timestamps backend/test_course_generator.py::test_analyze_document_detects_documentation_from_code_blocks -v
```

Expected: pass.

### Task 4: Generate Course Assets

**Files:**
- Create: `backend/course_generator/planner.py`
- Test: `backend/test_course_generator.py`

- [ ] **Step 1: Add failing planner test**

Append:

```python
from course_generator.planner import build_course_package


def test_build_course_package_creates_modules_lessons_and_video_assets():
    document = parse_markdown("# AI Notes\n\n## Agents\n\nAgents use tools.\n\n## RAG\n\nRAG retrieves context.")
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
```

- [ ] **Step 2: Run planner test to verify it fails**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_build_course_package_creates_modules_lessons_and_video_assets -v
```

Expected: failure because `planner.py` does not exist.

- [ ] **Step 3: Implement planner**

Create `backend/course_generator/planner.py`:

```python
from .schemas import (
    AudienceLevel,
    ContentAnalysis,
    CoursePackage,
    LessonAsset,
    MarkdownDocument,
    ModuleAsset,
    QuizQuestion,
    TargetType,
    TransformationMode,
)


def _clean_heading(heading: str) -> str:
    return heading.strip().lstrip("0123456789:.- ").strip() or "Lesson"


def _summary_from_content(content: str) -> str:
    words = " ".join(content.split()).split()
    if not words:
        return "This lesson introduces the core ideas and turns them into practical learning steps."
    return " ".join(words[:80])


def _build_quiz(lesson_id: str, title: str) -> list[QuizQuestion]:
    return [
        QuizQuestion(
            id=f"{lesson_id}-q1",
            type="multiple_choice",
            question=f"What is the main purpose of the lesson '{title}'?",
            choices=[
                "Understand the key concept and apply it in practice",
                "Memorize unrelated terminology",
                "Skip the implementation details",
                "Avoid checking understanding",
            ],
            answer="Understand the key concept and apply it in practice",
            explanation="Each generated lesson is designed to teach a concept and connect it to practice.",
        )
    ]


def _slide_outline(title: str, explanation: str) -> str:
    return f"""# Slide Outline: {title}

## Slide 1: Lesson Goal
- What learners will understand
- Why the topic matters

## Slide 2: Core Concept
- {explanation[:160]}

## Slide 3: Practical Example
- Show a simple example
- Explain the decision points

## Slide 4: Exercise
- Give learners one concrete task

## Speaker Notes
Use original narration. Do not read source material word-for-word.
"""


def _video_script(title: str, explanation: str) -> str:
    return f"""# Video Script: {title}

## Hook
In this lesson, we will turn {title} into something you can use in a real project.

## Narration
{explanation}

## Demo Cue
Show a practical example or diagram that makes the concept concrete.

## Exercise Cue
Ask learners to apply the idea before moving to the next lesson.

## Outro
Summarize the key takeaway and preview the next lesson.
"""


def _storyboard(title: str) -> str:
    return f"""# Storyboard: {title}

| Scene | Visual | Narration | Duration |
| --- | --- | --- | --- |
| 1 | Title slide | Introduce the lesson goal | 20s |
| 2 | Concept diagram | Explain the core idea | 90s |
| 3 | Demo or example | Walk through the practical use | 180s |
| 4 | Exercise slide | Give the learner a task | 45s |
| 5 | Recap slide | Summarize and transition | 30s |
"""


def build_course_package(
    document: MarkdownDocument,
    analysis: ContentAnalysis,
    target: TargetType,
    transformation_mode: TransformationMode,
    course_goal: str,
) -> CoursePackage:
    lessons: list[LessonAsset] = []
    for index, section in enumerate(document.sections, start=1):
        lesson_id = f"lesson-01-{index:02d}"
        title = _clean_heading(section.heading)
        explanation = _summary_from_content(section.content)
        lessons.append(
            LessonAsset(
                id=lesson_id,
                title=title,
                learning_objectives=[
                    f"Explain the purpose of {title}.",
                    f"Apply {title} in a practical learning activity.",
                ],
                explanation=explanation,
                exercise=f"Create a short example that demonstrates {title}.",
                quiz=_build_quiz(lesson_id, title),
                slide_outline=_slide_outline(title, explanation),
                video_script=_video_script(title, explanation),
                storyboard=_storyboard(title),
            )
        )

    module = ModuleAsset(
        id="module-01",
        title=document.title,
        description=f"{course_goal} Source type detected: {analysis.source_type}.",
        lessons=lessons,
    )

    return CoursePackage(
        title=document.title,
        description=f"A {analysis.audience_level} course generated from Markdown source material.",
        target=target,
        audience_level=analysis.audience_level,
        transformation_mode=transformation_mode,
        learning_outcomes=[
            f"Understand the main ideas in {document.title}.",
            "Apply the material through exercises and lesson activities.",
            "Complete a final project that combines the course concepts.",
        ],
        prerequisites=["Basic familiarity with the topic area."],
        modules=[module],
        final_project=f"Build a practical project that demonstrates the core ideas from {document.title}.",
    )
```

- [ ] **Step 4: Run planner test**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_build_course_package_creates_modules_lessons_and_video_assets -v
```

Expected: pass.

### Task 5: Export Course Package Files

**Files:**
- Create: `backend/course_generator/exporter.py`
- Test: `backend/test_course_generator.py`

- [ ] **Step 1: Add failing exporter test**

Append:

```python
from course_generator.exporter import export_course_package


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
```

- [ ] **Step 2: Run exporter test to verify it fails**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_export_course_package_writes_markdown_json_and_zip -v
```

Expected: failure because `exporter.py` does not exist.

- [ ] **Step 3: Implement exporter**

Create `backend/course_generator/exporter.py`:

```python
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
    quiz = "\n".join(f"- {question.question}" for question in lesson.quiz)
    return f"""# {lesson.title}

Course: {course_title}
Module: {module_title}

## Learning Objectives
{objectives}

## Explanation
{lesson.explanation}

## Exercise
{lesson.exercise}

## Quiz
{quiz}
"""


def export_course_package(course: CoursePackage, output_root: str | Path) -> tuple[Path, Path]:
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
        _write(package_dir / "modules" / f"{module.id}.md", f"# {module.title}\n\n{module.description}\n")
        youtube_lines.append(f"## {module.title}")
        for lesson in module.lessons:
            _write(
                package_dir / "lessons" / f"{lesson.id}.md",
                _lesson_markdown(course.title, module.title, lesson),
            )
            _write(package_dir / "slides" / f"{lesson.id}-slides.md", lesson.slide_outline)
            _write(package_dir / "scripts" / f"{lesson.id}-video-script.md", lesson.video_script)
            _write(package_dir / "storyboards" / f"{lesson.id}-storyboard.md", lesson.storyboard)
            quiz_questions.extend(question.model_dump() for question in lesson.quiz)
            exercises.append(f"## {lesson.title}\n\n{lesson.exercise}\n")
            youtube_lines.append(f"- {lesson.title}")

    _write(package_dir / "quizzes" / "quiz-bank.json", json.dumps({"questions": quiz_questions}, indent=2))
    _write(package_dir / "exercises" / "exercises.md", "\n".join(exercises))
    _write(package_dir / "youtube" / "playlist-plan.md", "\n".join(youtube_lines) + "\n")
    _write(package_dir / "youtube" / "lesson-metadata.md", "# Lesson Metadata\n\nAdd titles, descriptions, and chapters per lesson.\n")

    zip_base = str(package_dir)
    zip_file = shutil.make_archive(zip_base, "zip", package_dir)
    return package_dir, Path(zip_file)
```

- [ ] **Step 4: Run exporter test**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_export_course_package_writes_markdown_json_and_zip -v
```

Expected: pass.

### Task 6: Add Service Layer

**Files:**
- Create: `backend/course_generator/service.py`
- Test: `backend/test_course_generator.py`

- [ ] **Step 1: Add failing service test**

Append:

```python
from course_generator.schemas import CoursePlanRequest
from course_generator.service import create_course_plan


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
```

- [ ] **Step 2: Run service test to verify it fails**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_create_course_plan_orchestrates_parser_analyzer_and_planner -v
```

Expected: failure because `service.py` does not exist.

- [ ] **Step 3: Implement service**

Create `backend/course_generator/service.py`:

```python
from pathlib import Path

from .analyzer import analyze_document
from .exporter import export_course_package
from .markdown_parser import parse_markdown
from .planner import build_course_package
from .schemas import CoursePlanRequest, CoursePlanResponse


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
```

- [ ] **Step 4: Run service test**

Run:

```powershell
python -m pytest backend/test_course_generator.py::test_create_course_plan_orchestrates_parser_analyzer_and_planner -v
```

Expected: pass.

### Task 7: Add FastAPI Endpoints

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/test_main.py`

- [ ] **Step 1: Add failing API tests**

Append to `backend/test_main.py`:

```python
def test_course_plan_endpoint_returns_course_package():
    response = client.post(
        "/course/plan",
        json={
            "markdown": "# Demo\n\n## Intro\n\nContent",
            "target": "both",
            "audience_level": "beginner",
            "transformation_mode": "original",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["course"]["title"] == "Demo"
    assert data["course"]["modules"][0]["lessons"][0]["title"] == "Intro"


def test_course_export_endpoint_creates_downloadable_zip():
    response = client.post(
        "/course/export",
        json={"markdown": "# Demo\n\n## Intro\n\nContent"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["package_id"]
    assert data["download_url"].startswith("/course/download/")

    download = client.get(data["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/zip")
```

- [ ] **Step 2: Run API tests to verify they fail**

Run:

```powershell
python -m pytest backend/test_main.py::test_course_plan_endpoint_returns_course_package backend/test_main.py::test_course_export_endpoint_creates_downloadable_zip -v
```

Expected: failure because endpoints do not exist.

- [ ] **Step 3: Add route imports and constants**

In `backend/main.py`, add:

```python
from course_generator.schemas import CourseExportResponse, CoursePlanRequest
from course_generator.service import create_course_export, create_course_plan
```

After `DOWNLOAD_DIR`, add:

```python
COURSE_EXPORT_DIR = os.path.join(BASE_DIR, "course_exports")
```

In `lifespan`, add:

```python
os.makedirs(COURSE_EXPORT_DIR, exist_ok=True)
```

- [ ] **Step 4: Add endpoints**

Add to `backend/main.py`:

```python
@app.post("/course/plan")
def plan_course(request: CoursePlanRequest):
    return create_course_plan(request)


@app.post("/course/export")
def export_course(request: CoursePlanRequest):
    os.makedirs(COURSE_EXPORT_DIR, exist_ok=True)
    _, zip_path = create_course_export(request, COURSE_EXPORT_DIR)
    package_id = os.path.splitext(os.path.basename(zip_path))[0]
    return CourseExportResponse(
        package_id=package_id,
        download_url=f"/course/download/{package_id}",
    )


@app.get("/course/download/{package_id}")
def download_course_package(package_id: str):
    if not re.match(r"^[a-zA-Z0-9_.-]+$", package_id):
        raise HTTPException(status_code=404, detail="Package not found")
    zip_path = os.path.realpath(os.path.join(COURSE_EXPORT_DIR, f"{package_id}.zip"))
    real_export_dir = os.path.realpath(COURSE_EXPORT_DIR)
    if not zip_path.startswith(real_export_dir + os.sep):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=404, detail="Package not found")
    return FileResponse(
        zip_path,
        filename=f"{package_id}.zip",
        media_type="application/zip",
    )
```

- [ ] **Step 5: Run API tests**

Run:

```powershell
python -m pytest backend/test_main.py::test_course_plan_endpoint_returns_course_package backend/test_main.py::test_course_export_endpoint_creates_downloadable_zip -v
```

Expected: pass.

### Task 8: Final Verification

**Files:**
- Verify: `backend/test_course_generator.py`
- Verify: `backend/test_main.py`
- Verify: `docs/course-generator/README.md`

- [ ] **Step 1: Run course generator unit tests**

Run:

```powershell
python -m pytest backend/test_course_generator.py -v
```

Expected: all course generator tests pass.

- [ ] **Step 2: Run backend API tests**

Run:

```powershell
python -m pytest backend/test_main.py -v
```

Expected: all backend tests pass.

- [ ] **Step 3: Run full backend test set**

Run:

```powershell
python -m pytest backend -v
```

Expected: all tests pass.

- [ ] **Step 4: Start server and smoke test**

Run:

```powershell
python -m uvicorn backend.main:app --port 8000
```

In another terminal:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/course/plan -ContentType "application/json" -Body '{"markdown":"# Demo\n\n## Intro\n\nContent"}'
```

Expected: JSON response contains `analysis` and `course`.

- [ ] **Step 5: Verify export download**

Run:

```powershell
$res = Invoke-RestMethod -Method Post http://127.0.0.1:8000/course/export -ContentType "application/json" -Body '{"markdown":"# Demo\n\n## Intro\n\nContent"}'
Invoke-WebRequest "http://127.0.0.1:8000$($res.download_url)" -OutFile "$env:TEMP\course.zip"
Test-Path "$env:TEMP\course.zip"
```

Expected: `True`.

## Acceptance Criteria

- Any non-empty Markdown can be submitted to `/course/plan`.
- The service returns a structured course package with modules and lessons.
- Each lesson includes learning objectives, explanation, exercise, quiz, slide outline, video script, and storyboard.
- `/course/export` creates a zip package with Markdown and JSON files.
- `/course/download/{package_id}` downloads only files inside the configured export directory.
- The feature is independent from YouTube transcript generation.
- Tests cover parser, analyzer, planner, exporter, service, and API endpoints.

## Future Enhancements

- Add optional LLM-based rewriting and enrichment.
- Add `.pptx` export for slide outlines.
- Add `.srt` and `.vtt` caption generation.
- Add Remotion or HyperFrames video rendering.
- Add image/diagram generation for slide visuals.
- Add user-selected teaching styles.
- Add plagiarism/similarity checks against source text.
- Add web UI for uploading Markdown and downloading the package.

