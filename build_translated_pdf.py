from __future__ import annotations

import html
import re
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent
SOURCE_PDF = ROOT / "Code_ Terraform.pdf"
TRANSLATIONS = ROOT / "output" / "translation"
OUT_DIR = ROOT / "output" / "pdf"
IMAGE_DIR = ROOT / "tmp" / "pdfs" / "translated-images"
OUT_PDF = OUT_DIR / "Code_Terraform_中文译本.pdf"
OUT_MD = OUT_DIR / "Code_Terraform_中文译本.md"

SEGMENTS = [
    (1, 20, "segment-early-01-pages-0001-0020.md"),
    (21, 40, "segment-early-02-pages-0021-0040.md"),
    (41, 60, "segment-early-03-pages-0041-0060.md"),
    (61, 80, "segment-early-04-pages-0061-0080.md"),
    (81, 100, "segment-early-05-pages-0081-0100.md"),
    (101, 120, "segment-early-06-pages-0101-0120.md"),
    (121, 140, "segment-early-07-pages-0121-0140.md"),
    (141, 160, "segment-early-08-pages-0141-0160.md"),
    (161, 180, "segment-early-09-pages-0161-0180.md"),
    (181, 200, "segment-early-10-pages-0181-0200.md"),
    (201, 220, "segment-early-11-pages-0201-0220.md"),
    (221, 240, "segment-early-12-pages-0221-0240.md"),
    (241, 252, "segment-early-13-pages-0241-0252.md"),
] + [
    (253 + 20 * i, min(272 + 20 * i, 1261), f"segment-{5+i:02d}-pages-{253+20*i:04d}-{min(272+20*i,1261):04d}.md")
    for i in range(51)
]


def parse_pages() -> dict[int, str]:
    pages: dict[int, str] = {}
    marker = re.compile(r"^#{1,3}\s*(?:\[[^\]]*\]\s*)?第\s*(\d+)\s*页[^\n]*$", re.M)
    for start, end, filename in SEGMENTS:
        text = (TRANSLATIONS / filename).read_text(encoding="utf-8")
        matches = list(marker.finditer(text))
        for idx, match in enumerate(matches):
            page = int(match.group(1))
            body = text[match.end(): matches[idx + 1].start() if idx + 1 < len(matches) else len(text)].strip()
            if start <= page <= end:
                if page in pages:
                    raise ValueError(f"duplicate page {page}")
                pages[page] = body
    missing = sorted(set(range(1, 1262)) - set(pages))
    if missing:
        raise ValueError(f"missing translated pages: {missing[:20]}")
    return pages


def extract_page_images() -> dict[int, list[Path]]:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    images: dict[int, list[Path]] = {}
    reader = PdfReader(SOURCE_PDF)
    for page_no, page in enumerate(reader.pages, start=1):
        paths: list[Path] = []
        for order, item in enumerate(page.images, start=1):
            suffix = Path(item.name).suffix or ".png"
            path = IMAGE_DIR / f"p{page_no:04d}-{order}{suffix}"
            if not path.exists():
                path.write_bytes(item.data)
            paths.append(path)
        if paths:
            images[page_no] = paths
    return images


def to_flowables(text: str, styles: dict[str, ParagraphStyle]):
    out = []
    in_code = False
    code: list[str] = []

    def inline(value: str) -> str:
        escaped = html.escape(value)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        return re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', escaped)

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                out.append(Preformatted("\n".join(code), styles["code"], maxLineLength=95))
                out.append(Spacer(1, 2 * mm))
                code = []
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        if not line.strip():
            out.append(Spacer(1, 1.4 * mm))
            continue
        if line.startswith("> "):
            line = line[2:]
        heading = re.match(r"^(#{1,6})\s*(.+)$", line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            style = "czh_h1" if level == 1 else "czh_h2" if level == 2 else "czh_h3"
            out.append(Paragraph(inline(title), styles[style]))
            continue
        if re.fullmatch(r"[-:| ]+", line):
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [inline(c.strip()) for c in line.strip("|").split("|")]
            if all(re.fullmatch(r"[-: ]+", c) for c in cells):
                continue
            table = Table([[Paragraph(c or " ", styles["table"]) for c in cells]], hAlign="LEFT")
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B9C2D0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F7FA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            out.append(table)
            continue
        bullet = re.match(r"^(?:[-*]|\d+\.)\s+(.*)", line)
        if bullet:
            out.append(Paragraph("• " + inline(bullet.group(1)), styles["body"]))
        else:
            out.append(Paragraph(inline(line).replace("  ", "<br/>"), styles["body"]))
    if code:
        out.append(Preformatted("\n".join(code), styles["code"], maxLineLength=95))
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = parse_pages()
    page_images = extract_page_images()
    OUT_MD.write_text("\n\n".join(f"## 第 {page} 页\n\n{pages[page]}" for page in range(1, 1262)), encoding="utf-8")

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="page", parent=styles["Heading1"], fontName="STSong-Light", fontSize=13, leading=17, textColor=colors.HexColor("#304E87"), spaceAfter=5 * mm))
    styles.add(ParagraphStyle(name="czh_h1", parent=styles["Heading1"], fontName="STSong-Light", fontSize=15, leading=20, spaceBefore=4 * mm, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="czh_h2", parent=styles["Heading2"], fontName="STSong-Light", fontSize=12, leading=16, spaceBefore=3 * mm, spaceAfter=1.5 * mm))
    styles.add(ParagraphStyle(name="czh_h3", parent=styles["Heading3"], fontName="STSong-Light", fontSize=10.5, leading=14, spaceBefore=2 * mm, spaceAfter=1 * mm))
    styles.add(ParagraphStyle(name="body", parent=styles["BodyText"], fontName="STSong-Light", fontSize=8.8, leading=13.2, spaceAfter=1.5 * mm))
    styles.add(ParagraphStyle(name="table", parent=styles["BodyText"], fontName="STSong-Light", fontSize=7.6, leading=10))
    styles.add(ParagraphStyle(name="code", fontName="Courier", fontSize=6.8, leading=8.5, leftIndent=3 * mm, rightIndent=3 * mm, backColor=colors.HexColor("#F2F4F7"), borderColor=colors.HexColor("#E1E5EB"), borderWidth=0.25, borderPadding=3))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("STSong-Light", 7)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Code: Terraform 中文译本  |  输出页 {doc.page}")
        canvas.restoreState()

    story = [Paragraph("《Code: Terraform》中文译本", ParagraphStyle(name="title", fontName="STSong-Light", fontSize=24, leading=32, alignment=TA_CENTER, spaceAfter=12 * mm)), Paragraph("术语采用中文（English）形式；代码、API、命令与标识符均保持原样。源文档中的嵌入图示已随页附入。", styles["body"]), PageBreak()]
    for page in range(1, 1262):
        story.append(Paragraph(f"源 PDF 第 {page} 页", styles["page"]))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#B9C2D0"), spaceAfter=3 * mm))
        story.extend(to_flowables(pages[page], styles))
        for image_path in page_images.get(page, []):
            try:
                image = Image(str(image_path))
                image._restrictSize(160 * mm, 80 * mm)
                story.extend([Spacer(1, 3 * mm), image])
            except Exception:
                pass
        if page != 1261:
            story.append(PageBreak())
    doc = SimpleDocTemplate(str(OUT_PDF), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=15 * mm, bottomMargin=16 * mm, title="Code: Terraform 中文译本", author="Codex")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"built {OUT_PDF}")
    print(f"translated_pages={len(pages)} image_pages={len(page_images)} images={sum(map(len, page_images.values()))}")


if __name__ == "__main__":
    main()
