"""
Non-Text Content Audit
-----------------------
Detects information that may exist only in non-text form (images, PDFs,
audio/video, inline SVG, CSS background-images) and would therefore be
invisible or degraded for text-based AI agents / crawlers, not just for
screen-reader users.

Design principle: avoid "existence = problem" rules. A PDF, an image, or
a background-image is not automatically an issue -- it's only an issue
when it plausibly carries information that has no text equivalent.
Every check below tries to reflect that, and downgrades confidence when
there's a plausible reason the finding is a false positive (e.g. a
caption right next to an unlabeled image).
"""

import json
import logging
import re
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import pytesseract
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("non_text_audit")

# ---------------------------------------------------------------------------
# Config (tune these in one place instead of hunting through the file)
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT = 10
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NonTextAuditBot/1.0; "
        "+https://example.com/bot)"
    )
}
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024  # safety cap for PDFs/images

MIN_OCR_TEXT_LENGTH = 10
MIN_MEANINGFUL_ALT_LENGTH = 10
MIN_IMAGE_DIMENSION_FOR_OCR = 40  # skip tiny icons/spacers/social buttons

GENERIC_ALT_WORDS = {
    "image", "photo", "picture", "graphic", "icon", "logo",
    "img", "banner", "untitled", "photo of", "image of",
}
FILENAME_ALT_PATTERN = re.compile(
    r"^(img|image|photo|pic|dsc|screenshot)?[\s_\-]*\d{2,}"
    r"(\.(jpe?g|png|gif|webp|svg))?$",
    re.IGNORECASE,
)

GENERIC_LINK_PHRASES = {
    "click here", "here", "download", "download pdf", "download here",
    "pdf", "view", "view pdf", "read more", "learn more", "link", "file",
    "document", "open", "open pdf", "click", "more",
}

CAPTION_TRACK_KINDS = {"captions", "descriptions", "subtitles"}
TRANSCRIPT_KEYWORDS = ("transcript", "transcription", "text version")
CAPTION_KEYWORDS = ("captions", "subtitles") + TRANSCRIPT_KEYWORDS

BG_IMAGE_PATTERN = re.compile(r"background(-image)?\s*:\s*url\(([^)]+)\)")

# process-level caches so repeated links/images on one page aren't re-fetched
_pdf_cache = {}
_image_cache = {}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def is_generic_alt(alt: str) -> bool:
    norm = _normalize(alt)
    if not norm:
        return False  # empty alt is handled separately (decorative)
    if norm in GENERIC_ALT_WORDS:
        return True
    if FILENAME_ALT_PATTERN.match(norm):
        return True
    if len(norm) <= 2:
        return True
    return False


def is_generic_link_text(text: str) -> bool:
    norm = _normalize(text)
    if norm in GENERIC_LINK_PHRASES:
        return True
    if len(norm) <= 2:
        return True
    return False


def get_link_description(link) -> str:
    """
    Resolve the best available accessible name for a link, in priority
    order matching how assistive tech / most spec-aligned parsers do it:
    aria-label > visible text > image alt text inside the link > title.
    """
    aria_label = link.get("aria-label")
    if aria_label and aria_label.strip():
        return aria_label.strip()

    link_text = link.get_text(" ", strip=True)
    if link_text:
        return link_text

    image_alts = []
    for img in link.find_all("img"):
        alt = (img.get("alt") or "").strip()
        if alt:
            image_alts.append(alt)
    if image_alts:
        return " ".join(image_alts)

    title = link.get("title")
    if title and title.strip():
        return title.strip()

    return ""


def _nearby_caption_context(img) -> str | None:
    """
    Returns a short note if the image has plausible surrounding context
    (figcaption or aria-describedby) that may reduce the real-world
    severity of a missing/weak alt text finding.
    """
    figure = img.find_parent("figure")
    if figure:
        figcaption = figure.find("figcaption")
        if figcaption and figcaption.get_text(strip=True):
            return "figcaption"

    described_by = img.get("aria-describedby")
    if described_by:
        return "aria-describedby"

    return None


def _has_accessible_name(el) -> bool:
    """Rough accessible-name check for a link/button wrapping an image."""
    if (el.get("aria-label") or "").strip():
        return True
    if el.get_text(strip=True):
        return True
    for img in el.find_all("img"):
        if (img.get("alt") or "").strip():
            return True
    return False


def _safe_get(url, stream=False):
    resp = requests.get(
        url, timeout=REQUEST_TIMEOUT, headers=REQUEST_HEADERS, stream=stream
    )
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# PDF checks
# ---------------------------------------------------------------------------

def check_pdf_text_content(pdf_url: str, index: int) -> list:
    findings = []

    if pdf_url in _pdf_cache:
        return _pdf_cache[pdf_url]

    try:
        if not pdf_url.startswith(("http://", "https://")):
            with open(pdf_url, "rb") as f:
                pdf_bytes = f.read()
        else:
            resp = _safe_get(pdf_url)
            if len(resp.content) > MAX_DOWNLOAD_BYTES:
                raise ValueError("PDF exceeds size cap for analysis")
            pdf_bytes = resp.content

        reader = PdfReader(BytesIO(pdf_bytes))
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
        num_pages = len(page_texts) or 1
        empty_pages = sum(1 for t in page_texts if len(t) < 20)
        full_text = "\n".join(page_texts).strip()

        if not full_text:
            findings.append({
                "id": f"NT005-{index}",
                "title": "PDF appears to be fully image-based / no extractable text",
                "type": "issue",
                "severity": "high",
                "confidence": "high",
                "evidence": (
                    f"'{pdf_url}' has no extractable text across "
                    f"{num_pages} page(s). Content likely exists only as "
                    "scanned images."
                ),
                "suggested_action": {
                    "summary": (
                        "Provide a text-based version or an HTML/text "
                        "equivalent of the document."
                    ),
                    "priority": "high",
                },
            })
        elif num_pages > 1 and (empty_pages / num_pages) >= 0.3:
            findings.append({
                "id": f"NT005b-{index}",
                "title": "PDF is partially image-based",
                "type": "warning",
                "severity": "medium",
                "confidence": "medium",
                "evidence": (
                    f"'{pdf_url}': {empty_pages} of {num_pages} pages have "
                    "little to no extractable text. Some content may be "
                    "inaccessible to text-based readers even though the "
                    "document as a whole is not fully scanned."
                ),
                "suggested_action": {
                    "summary": (
                        "Check the flagged pages -- provide text "
                        "equivalents for any scanned pages."
                    ),
                    "priority": "medium",
                },
            })

    except Exception as e:
        findings.append({
            "id": f"NT006-{index}",
            "title": "PDF could not be analyzed",
            "type": "warning",
            "severity": "low",
            "confidence": "low",
            "evidence": f"The PDF could not be downloaded or parsed: {e}",
            "suggested_action": {
                "summary": "Verify the PDF is publicly accessible and parseable.",
                "priority": "low",
            },
        })

    _pdf_cache[pdf_url] = findings
    return findings


# ---------------------------------------------------------------------------
# Image checks (alt text, OCR, functional images, inline SVG)
# ---------------------------------------------------------------------------

def check_image_text(image: Image.Image, index: int, visible_page_text: str) -> list:
    """OCR an image and flag it only if it contains text NOT already
    present as normal page text (avoids flagging redundant images)."""
    findings = []

    if image.width < MIN_IMAGE_DIMENSION_FOR_OCR or image.height < MIN_IMAGE_DIMENSION_FOR_OCR:
        return findings  # almost certainly an icon/spacer, not worth OCR

    try:
        detected_text = pytesseract.image_to_string(image).strip()
    except Exception:
        logger.warning("OCR failed for image #%s", index + 1, exc_info=True)
        return findings

    if len(detected_text) < MIN_OCR_TEXT_LENGTH:
        return findings

    # Suppress if this text is already present as real page text elsewhere
    # (e.g. an image duplicating a heading that's also rendered as HTML text)
    normalized_ocr = _normalize(detected_text)
    normalized_page = _normalize(visible_page_text)
    if normalized_ocr and normalized_ocr in normalized_page:
        return findings

    findings.append({
        "id": f"NT009-{index}",
        "title": "Image contains embedded text with no clear text equivalent",
        "type": "warning",
        "severity": "medium",
        "confidence": "medium",
        "evidence": (
            f"OCR detected text inside image #{index + 1} that does not "
            f"appear elsewhere on the page: '{detected_text[:200]}'"
        ),
        "suggested_action": {
            "summary": (
                "Provide this information as normal webpage text, or add "
                "a meaningful alt/long-description if it's purely visual."
            ),
            "priority": "medium",
        },
    })
    return findings


def check_inline_svg(soup) -> list:
    findings = []
    for index, svg in enumerate(soup.find_all("svg")):
        # crude complexity heuristic: >1 shape child suggests a real
        # graphic (icon/chart) rather than a trivial decorative mark
        shape_children = svg.find_all(["path", "circle", "rect", "polygon", "line"])
        if len(shape_children) <= 1:
            continue

        has_title = svg.find("title") is not None
        has_label = bool((svg.get("aria-label") or "").strip())
        is_hidden = svg.get("aria-hidden") == "true"

        if is_hidden:
            continue

        if not has_title and not has_label:
            findings.append({
                "id": f"NT011-{index}",
                "title": "Inline SVG graphic has no accessible text equivalent",
                "type": "warning",
                "severity": "medium",
                "confidence": "low",
                "evidence": (
                    f"Inline <svg> #{index + 1} has {len(shape_children)} "
                    "shape elements (may be an icon, chart, or diagram) but "
                    "no <title> or aria-label."
                ),
                "suggested_action": {
                    "summary": "Add a <title> or aria-label describing the SVG's content.",
                    "priority": "low",
                },
            })
    return findings


def check_background_images(soup) -> list:
    """
    Best-effort, low-confidence detection only. We can't tell from static
    HTML/inline CSS alone whether a background-image is decorative or
    carries information -- that needs a rendered layout. This is flagged
    as informational, not asserted as an issue.
    """
    findings = []
    seen = set()

    candidates = soup.find_all(style=True)
    for el in candidates:
        style = el.get("style", "")
        match = BG_IMAGE_PATTERN.search(style)
        if not match:
            continue
        url = match.group(2).strip("'\" ")
        if url in seen:
            continue
        seen.add(url)

        # only worth a flag if the element also has no text content at all
        # and isn't just a spacer (has some explicit sizing)
        if el.get_text(strip=True):
            continue

        findings.append({
            "id": f"NT012-{len(findings)}",
            "title": "CSS background-image detected with no adjacent text",
            "type": "info",
            "severity": "low",
            "confidence": "low",
            "evidence": (
                f"Element uses a CSS background-image ('{url}') and has no "
                "text content. This cannot be reliably classified as "
                "decorative vs. informative from static HTML alone -- "
                "flagged for manual review."
            ),
            "suggested_action": {
                "summary": (
                    "Manually verify: if this image conveys information, "
                    "provide a text equivalent nearby."
                ),
                "priority": "low",
            },
        })

    return findings


# ---------------------------------------------------------------------------
# Multimedia checks
# ---------------------------------------------------------------------------

def _has_caption_track(media_el) -> bool:
    for track in media_el.find_all("track"):
        if (track.get("kind") or "").lower() in CAPTION_TRACK_KINDS:
            return True
    return False


def check_multimedia(soup) -> list:
    findings = []

    for index, audio in enumerate(soup.find_all("audio")):
        if _has_caption_track(audio):
            continue  # strong signal present, no need for keyword guessing

        parent_text = _normalize(audio.parent.get_text(" ", strip=True))
        has_keyword_hint = any(k in parent_text for k in TRANSCRIPT_KEYWORDS)

        findings.append({
            "id": f"NT007-{index}",
            "title": "Audio may not have a text equivalent",
            "type": "warning",
            "severity": "medium" if not has_keyword_hint else "low",
            "confidence": "medium" if not has_keyword_hint else "low",
            "evidence": (
                f"Audio element #{index + 1} has no <track> element, and "
                + (
                    "nearby text loosely suggests a transcript may exist "
                    "(keyword match only -- verify manually)."
                    if has_keyword_hint
                    else "no nearby text suggests a transcript exists."
                )
            ),
            "suggested_action": {
                "summary": "Provide a transcript when the audio conveys important information.",
                "priority": "medium" if not has_keyword_hint else "low",
            },
        })

    for index, video in enumerate(soup.find_all("video")):
        if _has_caption_track(video):
            continue

        parent_text = _normalize(video.parent.get_text(" ", strip=True))
        has_keyword_hint = any(k in parent_text for k in CAPTION_KEYWORDS)

        findings.append({
            "id": f"NT008-{index}",
            "title": "Video may not have captions or a text equivalent",
            "type": "warning",
            "severity": "medium" if not has_keyword_hint else "low",
            "confidence": "medium" if not has_keyword_hint else "low",
            "evidence": (
                f"Video element #{index + 1} has no <track kind='captions'> "
                "element, and "
                + (
                    "nearby text loosely suggests captions/transcript may "
                    "exist (keyword match only -- verify manually)."
                    if has_keyword_hint
                    else "no nearby text suggests one exists."
                )
            ),
            "suggested_action": {
                "summary": "Provide captions or a transcript when the video conveys important information.",
                "priority": "medium" if not has_keyword_hint else "low",
            },
        })

    return findings


# ---------------------------------------------------------------------------
# Main audit
# ---------------------------------------------------------------------------

def audit_non_text(html: str, url: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    visible_page_text = soup.get_text(" ", strip=True)
    findings = []

    # --- PDF links -----------------------------------------------------
    pdf_links = soup.find_all("a", href=lambda h: h and ".pdf" in h.lower())
    for index, link in enumerate(pdf_links):
        pdf_url = link.get("href")
        pdf_findings = check_pdf_text_content(pdf_url, index)
        findings.extend(pdf_findings)

        fully_scanned = any(f["id"] == f"NT005-{index}" for f in pdf_findings)
        if not fully_scanned:
            description = get_link_description(link)
            findings.append({
                "id": f"NT003-{index}",
                "title": "PDF content may not have a webpage text equivalent",
                "type": "warning",
                "severity": "medium",
                "confidence": "medium",
                "evidence": (
                    f"Page links to a PDF: {description or pdf_url}. "
                    "Important information may be available only inside the document."
                ),
                "suggested_action": {
                    "summary": "Provide important PDF information as searchable webpage text or a concise HTML summary.",
                    "priority": "medium",
                },
            })

        description = get_link_description(link)
        if is_generic_link_text(description):
            findings.append({
                "id": f"NT004-{index}",
                "title": "PDF link has non-descriptive text",
                "type": "warning",
                "severity": "low",
                "confidence": "high",
                "evidence": (
                    f"PDF link uses the text '{description or '[empty]'}', "
                    "which gives little information about the document."
                ),
                "suggested_action": {
                    "summary": "Use descriptive link text, aria-label, or image alt text that identifies the document.",
                    "priority": "low",
                },
            })

    # --- Images ----------------------------------------------------------
    for index, img in enumerate(soup.find_all("img")):
        alt = img.get("alt")
        parent_link_or_button = img.find_parent(["a", "button"])
        is_functional = parent_link_or_button is not None

        if alt is None:
            if is_functional and not _has_accessible_name(parent_link_or_button):
                findings.append({
                    "id": f"NT010-{index}",
                    "title": "Functional image has no accessible name",
                    "type": "issue",
                    "severity": "high",
                    "confidence": "high",
                    "evidence": (
                        f"Image #{index + 1} is the only content of a "
                        "link/button and has no alt text, aria-label, or "
                        "visible text -- its function is not conveyed as text."
                    ),
                    "suggested_action": {
                        "summary": "Add descriptive alt text or aria-label describing what the control does.",
                        "priority": "high",
                    },
                })
            else:
                caption_ctx = _nearby_caption_context(img)
                findings.append({
                    "id": f"NT001-{index}",
                    "title": "Image may contain information that is not available as text",
                    "type": "issue",
                    "severity": "medium" if not caption_ctx else "low",
                    "confidence": "medium" if not caption_ctx else "low",
                    "evidence": (
                        f"Image #{index + 1} has no alt text."
                        + (
                            f" Nearby {caption_ctx} may provide partial context, "
                            "but should not be assumed sufficient."
                            if caption_ctx
                            else " If it conveys meaningful information, that "
                            "information may not be available as text."
                        )
                    ),
                    "suggested_action": {
                        "summary": "Provide a meaningful text alternative when the image conveys important information.",
                        "priority": "medium" if not caption_ctx else "low",
                    },
                })
        else:
            alt = alt.strip()
            if alt == "":
                continue  # legitimately decorative
            if is_generic_alt(alt):
                findings.append({
                    "id": f"NT002-{index}",
                    "title": "Image has a generic or filename-style text alternative",
                    "type": "warning",
                    "severity": "low",
                    "confidence": "high",
                    "evidence": (
                        f"Image #{index + 1} uses alt text '{alt}', which "
                        "does not communicate its actual information."
                    ),
                    "suggested_action": {
                        "summary": "Replace with a meaningful description when the image is informative.",
                        "priority": "low",
                    },
                })

        # OCR pass (skip if alt is already meaningfully descriptive)
        if alt and len(alt.strip()) >= MIN_MEANINGFUL_ALT_LENGTH:
            continue

        src = img.get("src")
        if src and src.startswith(("http://", "https://")):
            if src in _image_cache:
                pil_image = _image_cache[src]
            else:
                try:
                    resp = _safe_get(src, stream=True)
                    content = resp.raw.read(MAX_DOWNLOAD_BYTES + 1)
                    if len(content) > MAX_DOWNLOAD_BYTES:
                        pil_image = None
                    else:
                        pil_image = Image.open(BytesIO(content))
                        pil_image.load()
                except Exception:
                    logger.warning("Could not fetch image %s", src, exc_info=True)
                    pil_image = None
                _image_cache[src] = pil_image

            if pil_image is not None:
                findings.extend(check_image_text(pil_image, index, visible_page_text))

    # --- Inline SVG / background-images / multimedia ----------------------
    findings.extend(check_inline_svg(soup))
    findings.extend(check_background_images(soup))
    findings.extend(check_multimedia(soup))

    return findings


def summarize_findings(findings: list) -> dict:
    summary = {"total": len(findings), "by_severity": {}, "by_type": {}}
    for f in findings:
        summary["by_severity"][f["severity"]] = summary["by_severity"].get(f["severity"], 0) + 1
        summary["by_type"][f["type"]] = summary["by_type"].get(f["type"], 0) + 1
    return summary


if __name__ == "__main__":
    with open("test.html", "r", encoding="utf-8") as f:
        html = f.read()

    results = audit_non_text(html, "https://example.com")

    output = {
        "status": "issues_found" if results else "pass",
        "summary": summarize_findings(results),
        "findings": results,
    }
    print(json.dumps(output, indent=2))