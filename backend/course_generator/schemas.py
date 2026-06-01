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
