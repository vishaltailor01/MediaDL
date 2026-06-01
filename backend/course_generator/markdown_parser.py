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


def _extract_links(text: str) -> list[str]:
    return [link.rstrip(".,;:!?") for link in LINK_RE.findall(text)]


def parse_markdown(markdown: str) -> MarkdownDocument:
    matches = list(HEADING_RE.finditer(markdown))
    title = "Untitled Course"
    sections: list[MarkdownSection] = []

    if matches and matches[0].group(1) == "#":
        title = matches[0].group(2).strip()

    content_matches = matches[1:] if matches and matches[0].group(1) == "#" else matches
    for index, match in enumerate(content_matches):
        start = match.end()
        end = (
            content_matches[index + 1].start()
            if index + 1 < len(content_matches)
            else len(markdown)
        )
        section_content = markdown[start:end].strip()
        searchable_content = _strip_code_blocks(section_content)
        sections.append(
            MarkdownSection(
                level=len(match.group(1)),
                heading=match.group(2).strip(),
                content=section_content,
                timestamps=TIMESTAMP_RE.findall(
                    match.group(2) + "\n" + searchable_content
                ),
                code_blocks=_extract_code_blocks(section_content),
                links=_extract_links(searchable_content),
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
                links=_extract_links(searchable_content),
            )
        )

    return MarkdownDocument(title=title, raw_markdown=markdown, sections=sections)
