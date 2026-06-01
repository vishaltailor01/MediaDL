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
    if code_count >= 1 and (
        "api" in raw_lower or "install" in raw_lower or "usage" in raw_lower
    ):
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
    segmentation_strategy = (
        "timestamps" if source_type == "transcript" and timestamp_count else "headings"
    )
    recommended_lesson_count = max(1, min(24, len(document.sections)))

    return ContentAnalysis(
        source_type=source_type,
        topic=document.title,
        audience_level=audience_level,
        recommended_lesson_count=recommended_lesson_count,
        segmentation_strategy=segmentation_strategy,
    )
