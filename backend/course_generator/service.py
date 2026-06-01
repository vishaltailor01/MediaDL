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
