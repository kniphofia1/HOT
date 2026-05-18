from __future__ import annotations

from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile


def render_markdown_html(title: str, markdown: str) -> str:
    body_lines: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            body_lines.append("<br>")
        elif stripped.startswith("### "):
            body_lines.append(f"<h3>{escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            body_lines.append(f"<h2>{escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            body_lines.append(f"<h1>{escape(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            body_lines.append(f"<p class=\"bullet\">{escape(stripped)}</p>")
        elif stripped[0:2].isdigit() and ". " in stripped[:4]:
            body_lines.append(f"<p class=\"bullet\">{escape(stripped)}</p>")
        else:
            body_lines.append(f"<p>{escape(stripped)}</p>")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ max-width: 840px; margin: 48px auto; color: #111827; font-family: Arial, "Microsoft YaHei", sans-serif; line-height: 1.72; }}
    h1 {{ font-size: 30px; margin: 0 0 24px; }}
    h2 {{ margin-top: 34px; border-bottom: 1px solid #d1d5db; padding-bottom: 8px; }}
    h3 {{ margin-top: 26px; }}
    p {{ margin: 8px 0; }}
    .bullet {{ padding-left: 14px; }}
    @media print {{ body {{ margin: 24mm 18mm; }} }}
  </style>
</head>
<body>
{chr(10).join(body_lines)}
</body>
</html>"""


def render_markdown_docx(markdown: str) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", _content_types_xml())
        docx.writestr("_rels/.rels", _rels_xml())
        docx.writestr("word/document.xml", _document_xml(markdown))
    return buffer.getvalue()


def _document_xml(markdown: str) -> str:
    paragraphs = [_paragraph_xml(line) for line in markdown.splitlines()]
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {''.join(paragraphs)}
    <w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>
  </w:body>
</w:document>"""


def _paragraph_xml(line: str) -> str:
    stripped = line.strip()
    style = "Normal"
    text = stripped
    if stripped.startswith("### "):
        style = "Heading3"
        text = stripped[4:]
    elif stripped.startswith("## "):
        style = "Heading2"
        text = stripped[3:]
    elif stripped.startswith("# "):
        style = "Heading1"
        text = stripped[2:]
    return (
        "<w:p>"
        f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>"
        f"<w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"
        "</w:p>"
    )


def _content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""


def _rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
