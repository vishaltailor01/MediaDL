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


def parse_course_markdown(markdown_text: str) -> list[dict]:
    """
    Parses a markdown course file and yields a clean list of segments:
    [{"timestamp": str, "title": str, "script": str, "code_snippet": str}]
    """
    try:
        import markdown
        from bs4 import BeautifulSoup
        import re
        
        # Parse markdown to HTML with fenced code blocks extension enabled
        html = markdown.markdown(markdown_text, extensions=['fenced_code'])
        soup = BeautifulSoup(html, 'html.parser')
        
        segments = []
        # Fallback default segment if content appears before first heading
        current_segment = {
            "timestamp": "00:00",
            "title": "Introduction",
            "script": [],
            "code_snippet": []
        }
        
        timestamp_re = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b")
        
        for element in soup.children:
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                heading_text = element.get_text().strip()
                ts_match = timestamp_re.search(heading_text)
                if ts_match:
                    timestamp = ts_match.group(1)
                    title = heading_text.replace(timestamp, "").strip().strip("-").strip()
                else:
                    timestamp = "00:00"
                    title = heading_text
                
                # Save previous segment if it contains any content
                if current_segment and (current_segment["script"] or current_segment["code_snippet"]):
                    segments.append(current_segment)
                
                current_segment = {
                    "timestamp": timestamp,
                    "title": title,
                    "script": [],
                    "code_snippet": []
                }
            elif element.name == 'pre':
                code_elem = element.find('code')
                code_text = code_elem.get_text() if code_elem else element.get_text()
                if current_segment:
                    current_segment["code_snippet"].append(code_text)
            elif element.name in ['p', 'ul', 'ol', 'blockquote', 'div']:
                text = element.get_text().strip()
                if text and current_segment:
                    current_segment["script"].append(text)
                    
        # Append the final segment if it has content or a title
        if current_segment and (current_segment["script"] or current_segment["code_snippet"] or current_segment["title"]):
            segments.append(current_segment)
            
        # Clean up lists by joining text and stripping whitespaces
        cleaned_segments = []
        for seg in segments:
            script_str = "\n".join(seg["script"]).strip()
            code_str = "\n\n".join(seg["code_snippet"]).strip()
            cleaned_segments.append({
                "timestamp": seg["timestamp"],
                "title": seg["title"],
                "script": script_str,
                "code_snippet": code_str
            })
        return cleaned_segments
        
    except Exception as exc:
        # Graceful regex fallback if BeautifulSoup or markdown libraries fail
        import re
        timestamp_re = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b")
        code_block_re = re.compile(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```", re.DOTALL)
        
        # Split text by heading patterns
        sections = re.split(r"^(#+)\s+(.+)$", markdown_text, flags=re.MULTILINE)
        
        cleaned_segments = []
        # If there is initial content before first heading
        if sections and not sections[0].strip().startswith("#"):
            initial_text = sections[0].strip()
            if initial_text:
                codes = code_block_re.findall(initial_text)
                stripped_text = code_block_re.sub("", initial_text).strip()
                cleaned_segments.append({
                    "timestamp": "00:00",
                    "title": "Introduction",
                    "script": stripped_text,
                    "code_snippet": "\n\n".join(codes).strip()
                })
                
        # Parse alternating list: [h_level, h_text, content, ...]
        i = 1
        while i < len(sections):
            heading_text = sections[i+1].strip()
            content_text = sections[i+2].strip() if i+2 < len(sections) else ""
            
            ts_match = timestamp_re.search(heading_text)
            if ts_match:
                timestamp = ts_match.group(1)
                title = heading_text.replace(timestamp, "").strip().strip("-").strip()
            else:
                timestamp = "00:00"
                title = heading_text
                
            codes = code_block_re.findall(content_text)
            stripped_text = code_block_re.sub("", content_text).strip()
            
            cleaned_segments.append({
                "timestamp": timestamp,
                "title": title,
                "script": stripped_text,
                "code_snippet": "\n\n".join(codes).strip()
            })
            i += 3
            
        return cleaned_segments

