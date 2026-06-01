# Generic Markdown Course Asset Generator

## Purpose

The course generator converts any Markdown source file into a structured course asset package for YouTube publishing, web-app delivery, or both.

The input Markdown is treated as source material, not as final course copy. The generated course should be instructional, original, and reusable across different content types such as transcripts, blog posts, documentation, lecture notes, tutorials, research summaries, and mixed notes.

## Goals

- Accept generic `.md` input.
- Detect the source type and structure without assuming it came from YouTube.
- Produce a course blueprint with modules, lessons, outcomes, exercises, quizzes, and a final project.
- Generate presentation and video-production assets for each lesson.
- Export machine-readable JSON for a web course app.
- Keep the transformation rights-safe by default.

## Non-Goals

- Do not copy the source Markdown into finished lesson narration.
- Do not generate a complete video file in the first version.
- Do not require the input to contain timestamps.
- Do not assume the subject is AI or programming.
- Do not upload directly to YouTube or a web course platform in the first version.

## Rights-Safe Transformation Rules

The system should default to `transformation_mode = "original"`.

Allowed:

- Extract topic lists.
- Identify likely modules and lessons.
- Rewrite explanations in a new instructional voice.
- Create new examples, exercises, quizzes, and project tasks.
- Cite source links found in the Markdown as resources.

Avoid:

- Reusing long source passages as narration.
- Preserving another creator's exact sequence when a better course sequence is possible.
- Copying creator-specific intros, promotions, anecdotes, or examples.
- Reusing code, slides, screenshots, or assets unless the user has rights.

## Input Types

The analyzer should classify input as one of:

- `transcript`
- `article`
- `documentation`
- `tutorial`
- `lecture_notes`
- `meeting_notes`
- `research_notes`
- `unknown`

Classification should use observable Markdown features:

- transcript metadata or timestamps
- heading density
- code block count
- link count
- bullet list density
- prose length
- repeated conversational phrases

## Output Package

The first production version should generate this package:

```text
course-package/
  course-outline.md
  course.json
  modules/
    module-01.md
  lessons/
    lesson-01-01.md
  slides/
    lesson-01-01-slides.md
  scripts/
    lesson-01-01-video-script.md
  storyboards/
    lesson-01-01-storyboard.md
  quizzes/
    quiz-bank.json
  exercises/
    exercises.md
  youtube/
    playlist-plan.md
    lesson-metadata.md
  web/
    web-course.json
```

## Asset Types

### Course Outline

Contains:

- course title
- audience
- level
- prerequisites
- learning outcomes
- module list
- lesson list
- final project brief

### Lesson Plan

Each lesson contains:

- lesson title
- learning objectives
- original explanation
- example or demo idea
- exercise
- quiz questions
- summary
- resources

### Slide Outline

Each lesson slide outline contains:

- slide number
- slide title
- bullet points
- visual direction
- speaker notes

This can later be converted to `.pptx`, Google Slides, PDF, or HTML slides.

### Video Script

Each script contains:

- hook
- instructor narration
- screen recording cues
- code demo cues
- transition notes
- outro

### Storyboard

Each storyboard contains:

- scene number
- visual type
- on-screen text
- narration summary
- estimated duration

### Quiz Bank

The quiz bank should be JSON so a web app can render it:

```json
{
  "questions": [
    {
      "id": "q-001",
      "lessonId": "lesson-01-01",
      "type": "multiple_choice",
      "question": "What is the main purpose of this lesson?",
      "choices": ["A", "B", "C", "D"],
      "answer": "A",
      "explanation": "..."
    }
  ]
}
```

### Web Course JSON

The web export should be stable and versioned:

```json
{
  "schemaVersion": "1.0",
  "course": {
    "title": "...",
    "description": "...",
    "level": "beginner",
    "modules": []
  }
}
```

## Backend Architecture

Recommended backend package:

```text
backend/course_generator/
  __init__.py
  analyzer.py
  exporter.py
  markdown_parser.py
  planner.py
  schemas.py
  service.py
```

Responsibilities:

- `schemas.py`: Pydantic request/response and course package models.
- `markdown_parser.py`: converts Markdown text into structured sections.
- `analyzer.py`: classifies source type, topic, level, and content shape.
- `planner.py`: builds course modules, lessons, and asset drafts.
- `exporter.py`: writes Markdown and JSON package files.
- `service.py`: orchestration layer used by FastAPI endpoints and tests.

## API Shape

### Create Course Plan

```http
POST /course/plan
```

Request:

```json
{
  "markdown": "# Input...",
  "target": "both",
  "audience_level": "beginner",
  "transformation_mode": "original",
  "course_goal": "Teach this material as a practical course"
}
```

Response:

```json
{
  "course": {},
  "assets": {}
}
```

### Export Course Package

```http
POST /course/export
```

Request:

```json
{
  "markdown": "# Input...",
  "target": "both",
  "audience_level": "beginner",
  "transformation_mode": "original"
}
```

Response:

```json
{
  "package_id": "...",
  "download_url": "/course/download/..."
}
```

## Generation Strategy

Version 1 should be deterministic and local:

- Parse headings and content.
- Use heuristics to infer sections and lessons.
- Generate templates and concise original summaries.
- Avoid requiring an LLM.

Version 2 can add optional LLM enrichment:

- rewrite lessons in a selected teaching voice
- generate more polished slides and scripts
- create diagrams
- create alternative course levels

## Quality Criteria

A generated course package is acceptable when:

- it has a clear audience and learning outcomes
- modules follow a logical progression
- each lesson has an objective, explanation, exercise, and quiz
- video assets are usable by a creator without reading the source Markdown again
- web JSON validates against the schema
- source text is transformed, not copied wholesale

