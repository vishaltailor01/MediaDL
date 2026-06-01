import re

from .schemas import (
    ContentAnalysis,
    CoursePackage,
    LessonAsset,
    MarkdownDocument,
    ModuleAsset,
    QuizQuestion,
    TargetType,
    TransformationMode,
)

TIMESTAMP_CHAPTER_RE = re.compile(
    r"^\s*(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)\s*$", re.MULTILINE
)
METADATA_HEADINGS = {
    "video metadata",
    "metadata",
    "description",
    "transcript",
    "timestamps",
    "timestamp",
}


def _clean_heading(heading: str) -> str:
    return heading.strip().lstrip("0123456789:.- ").strip() or "Lesson"


def _summary_from_content(content: str) -> str:
    words = " ".join(content.split()).split()
    if not words:
        return "This lesson introduces the core ideas and turns them into practical learning steps."
    return " ".join(words[:80])


def _chunk_text(text: str, chunk_count: int) -> list[str]:
    words = " ".join(text.split()).split()
    if chunk_count <= 0:
        return []
    if not words:
        return [""] * chunk_count

    chunk_size = max(1, (len(words) + chunk_count - 1) // chunk_count)
    chunks = []
    for index in range(chunk_count):
        start = index * chunk_size
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
    return chunks


def _primary_course_title(document: MarkdownDocument) -> str:
    if document.title.lower() in {"youtube", "video", "transcript"}:
        for section in document.sections:
            if section.level == 2 and section.heading.strip():
                return _clean_heading(section.heading)
    return _clean_heading(document.title)


def _transcript_text(document: MarkdownDocument) -> str:
    for section in document.sections:
        if section.heading.strip().lower() == "transcript" and section.content.strip():
            return section.content.strip()
    return document.raw_markdown.strip()


def _timestamp_chapters(document: MarkdownDocument) -> list[str]:
    chapters = []
    for match in TIMESTAMP_CHAPTER_RE.finditer(document.raw_markdown):
        title = _clean_heading(match.group(2))
        if title.lower() not in METADATA_HEADINGS:
            chapters.append(title)
    return chapters


def _course_sections(document: MarkdownDocument, analysis: ContentAnalysis):
    if analysis.source_type == "transcript":
        chapters = _timestamp_chapters(document)
        if len(chapters) >= 2:
            chunks = _chunk_text(_transcript_text(document), len(chapters))
            return [
                (title, chunks[index] if index < len(chunks) else "")
                for index, title in enumerate(chapters)
            ]

        transcript_text = _transcript_text(document)
        if transcript_text:
            return [(_primary_course_title(document), transcript_text)]

    sections = [
        (section.heading, section.content)
        for section in document.sections
        if section.heading.strip().lower() not in METADATA_HEADINGS
    ]
    return sections or [(document.title, document.raw_markdown)]


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
            explanation=(
                "Each generated lesson is designed to teach a concept and connect "
                "it to practice."
            ),
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
    course_title = _primary_course_title(document)
    course_sections = _course_sections(document, analysis)
    lessons: list[LessonAsset] = []
    for index, (section_heading, section_content) in enumerate(course_sections, start=1):
        lesson_id = f"lesson-01-{index:02d}"
        title = _clean_heading(section_heading)
        explanation = _summary_from_content(section_content)
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
        title=course_title,
        description=f"{course_goal} Source type detected: {analysis.source_type}.",
        lessons=lessons,
    )

    return CoursePackage(
        title=course_title,
        description=(
            f"A {analysis.audience_level} course generated from Markdown source "
            "material."
        ),
        target=target,
        audience_level=analysis.audience_level,
        transformation_mode=transformation_mode,
        learning_outcomes=[
            f"Understand the main ideas in {course_title}.",
            "Apply the material through exercises and lesson activities.",
            "Complete a final project that combines the course concepts.",
        ],
        prerequisites=["Basic familiarity with the topic area."],
        modules=[module],
        final_project=(
            "Build a practical project that demonstrates the core ideas from "
            f"{course_title}."
        ),
    )
