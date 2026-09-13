#!/usr/bin/env python3
"""
engagement_audit.py

Audits on-site engagement using crawl artifacts produced by the
crawlability skill when available.

When invoked by audit-orchestrator:
    - DOES NOT perform a second site crawl.
    - Reuses HTML, URLs, statuses, and render artifacts already collected
      by crawlability.
    - Only performs additional read-only requests when a check genuinely
      requires information that crawlability did not collect (for example,
      testing a GET-based search endpoint).

When invoked standalone:
    - Falls back to its original read-only HTTP inspection behavior.

Scope:
    - findability
    - deep-entry orientation
    - broken links / dead ends
    - static mobile readiness
    - initial performance signals
    - search quality

It intentionally does not own:
    - sitemap/orphan-page detection
    - generic accessibility checks
    - structured data
    - crawlability/render-gap detection
"""

import argparse
import json
import re
import time

from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, quote
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


USER_AGENT = "EngagementAuditBot/1.0 (+read-only marketplace audit)"
REQUEST_TIMEOUT = 10

MAX_CRAWL_PAGES = 25

SLOW_RESPONSE_SECONDS = 3.0
ACCEPTABLE_RESPONSE_SECONDS = 1.5

MOBILE_VIEWPORT_WIDTH = 414

NON_CONTENT_PATH_HINTS = (
    "about",
    "contact",
    "privacy",
    "terms",
    "login",
    "signin",
    "sign-in",
    "signup",
    "sign-up",
    "cart",
    "checkout",
    "account",
)

GENERIC_LABELS = {
    "home",
    "menu",
    "more",
    "other",
    "misc",
    "info",
    "page",
    "about",
    "contact",
    "login",
    "sign in",
    "sign up",
    "cart",
}


session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

_finding_counter = 0


# ---------------------------------------------------------------------------
# Finding helpers
# ---------------------------------------------------------------------------

def next_id():
    global _finding_counter
    _finding_counter += 1
    return f"F-eng-{_finding_counter:03d}"


def make_finding(
    type_,
    title,
    severity,
    evidence,
    summary,
    steps,
    priority,
):
    return {
        "id": next_id(),
        "type": type_,
        "severity": severity,
        "title": title,
        "evidence": evidence,
        "suggested_action": {
            "summary": summary,
            "steps": steps,
            "priority": priority,
        },
    }


# ---------------------------------------------------------------------------
# URL / HTML helpers
# ---------------------------------------------------------------------------

def same_domain(url_a, url_b):
    return urlparse(url_a).netloc == urlparse(url_b).netloc


def normalize_url(url):
    parsed = urlparse(url)

    path = parsed.path.rstrip("/") or "/"

    return f"{parsed.scheme}://{parsed.netloc}{path}"


def strip_fragment(url):
    return url.split("#")[0]


def strip_boilerplate_text(soup):
    copy = BeautifulSoup(str(soup), "html.parser")

    for tag in copy.select("nav, footer, header"):
        tag.decompose()

    return copy.get_text(separator=" ", strip=True)


def get_nav_links(soup, base_url):
    nav_candidates = soup.select(
        'nav, [role="navigation"], header nav, .nav, .navbar, .menu'
    )

    links = []
    seen = set()

    for nav in nav_candidates:
        for a in nav.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            text = a.get_text(strip=True)

            if href not in seen and text:
                seen.add(href)
                links.append((text, href))

    return links


def get_submenu_links(soup, base_url):
    sub_candidates = soup.select(
        'nav ul ul a[href], '
        'nav .submenu a[href], '
        'nav .dropdown-menu a[href], '
        '[role="navigation"] ul ul a[href]'
    )

    links = []
    seen = set()

    for a in sub_candidates:
        href = urljoin(base_url, a["href"])
        text = a.get_text(strip=True)

        if href not in seen and text:
            seen.add(href)
            links.append((text, href))

    return links


def get_featured_offerings(soup, base_url):
    """
    Find homepage-highlighted offerings that have an actual navigable link.

    Unlinked headings, footer headings, and visually hidden headings are
    intentionally excluded to reduce false positives.
    """

    offerings = []
    seen = set()

    footer_headings = set()

    for footer in soup.find_all("footer"):
        footer_headings.update(
            id(h)
            for h in footer.find_all(["h1", "h2", "h3"])
        )

    hidden_pattern = re.compile(
        r"visually.?hidden|sr.?only|screen.?reader",
        re.IGNORECASE,
    )

    def is_visually_hidden(tag):
        classes = " ".join(tag.get("class", []))

        if hidden_pattern.search(classes):
            return True

        style = tag.get("style", "")

        if "display:none" in style.replace(" ", "").lower():
            return True

        return False

    def find_link(tag):
        a = tag.find("a", href=True)

        if a:
            return a["href"]

        parent = tag.find_parent(
            ["div", "section", "li", "article", "a"]
        )

        if parent is not None:

            if parent.name == "a" and parent.get("href"):
                return parent["href"]

            a2 = parent.find("a", href=True)

            if a2:
                return a2["href"]

        return None

    for tag in soup.select("h2, h3"):

        if id(tag) in footer_headings:
            continue

        if is_visually_hidden(tag):
            continue

        text = tag.get_text(strip=True)

        if not text or len(text) >= 80:
            continue

        href = find_link(tag)

        if not href:
            continue

        full = urljoin(base_url, href)

        key = (text, full)

        if key not in seen:
            seen.add(key)
            offerings.append(key)

    for tag in soup.select(
        "[class*=feature] a[href], "
        "[class*=category] a[href], "
        "[class*=highlight] a[href]"
    ):

        if tag.find_parent("footer") is not None:
            continue

        text = tag.get_text(strip=True)
        href = tag.get("href")

        if text and href:

            full = urljoin(base_url, href)

            key = (text, full)

            if key not in seen:
                seen.add(key)
                offerings.append(key)

    return offerings


def guess_query_terms(soup):
    if soup is None:
        return []

    candidates = []

    for tag in soup.select(
        "nav a, h2, h3, [class*=feature] a, [class*=category] a"
    ):

        if tag.find_parent("footer") is not None:
            continue

        text = tag.get_text(strip=True)

        if (
            text
            and 2 <= len(text) <= 30
            and text.lower() not in GENERIC_LABELS
        ):
            candidates.append(text.split()[0])

    seen = set()
    unique = []

    for candidate in candidates:

        if candidate.lower() not in seen:
            seen.add(candidate.lower())
            unique.append(candidate)

    unique.sort(key=len)

    return unique


# ---------------------------------------------------------------------------
# Crawl-artifact context
# ---------------------------------------------------------------------------

class CrawlContext:
    """
    Read-only view over the crawlability result.

    This is the key change that prevents engagement-audit from crawling
    pages that crawlability has already collected.
    """

    def __init__(self, crawl_audit=None):

        self.enabled = bool(
            crawl_audit
            and isinstance(crawl_audit, dict)
            and crawl_audit.get("pages")
        )

        self.pages = {}
        self.blocked_urls = set()

        if not self.enabled:
            return

        for blocked in crawl_audit.get("blockedUrls", []):
            self.blocked_urls.add(
                normalize_url(strip_fragment(blocked))
            )

        for page in crawl_audit.get("pages", []):

            requested = page.get("url")
            final_url = page.get("finalUrl")

            for candidate in (requested, final_url):

                if not candidate:
                    continue

                key = normalize_url(strip_fragment(candidate))

                self.pages[key] = page

    def get(self, url):
        if not self.enabled:
            return None

        key = normalize_url(strip_fragment(url))

        return self.pages.get(key)

    def all_pages(self):
        if not self.enabled:
            return []

        seen = set()
        result = []

        for page in self.pages.values():

            identity = id(page)

            if identity in seen:
                continue

            seen.add(identity)
            result.append(page)

        return result

    def has_page(self, url):
        return self.get(url) is not None


# ---------------------------------------------------------------------------
# Standalone fallback HTTP fetching
# ---------------------------------------------------------------------------

def fetch_live(url, allow_redirects=True):

    try:

        start = time.monotonic()

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=allow_redirects,
        )

        elapsed = time.monotonic() - start

        return {
            "url": url,
            "status": response.status_code,
            "html": response.text,
            "headers": dict(response.headers),
            "elapsed": elapsed,
            "error": None,
            "source": "live",
        }

    except requests.RequestException as error:

        return {
            "url": url,
            "status": None,
            "html": None,
            "headers": {},
            "elapsed": None,
            "error": str(error),
            "source": "live",
        }


def get_page(url, context):
    """
    Return a page from crawlability whenever possible.

    IMPORTANT:
    When a crawl context exists, this function never performs a second
    navigation request for a page already collected by crawlability.
    """

    if context.enabled:

        page = context.get(url)

        if page is not None:

            return {
                "url": page.get("finalUrl") or page.get("url") or url,
                "status": page.get("status"),
                "html": page.get("html"),
                "headers": {},
                "elapsed": None,
                "error": page.get("error"),
                "source": "crawlability",
                "crawl_page": page,
            }

    return fetch_live(url)


def status_desc(page):
    if page.get("error"):
        return page["error"]

    status = page.get("status")

    return f"HTTP {status if status is not None else 'unknown'}"


# ---------------------------------------------------------------------------
# Robots
# ---------------------------------------------------------------------------

def load_robots(site_url):
    """
    Only used for standalone execution.

    The orchestrator's crawlability skill already applies robots.txt before
    crawling, so engagement does not fetch robots.txt again when a crawl
    context is available.
    """

    robots_url = urljoin(site_url, "/robots.txt")

    rp = RobotFileParser()

    try:

        response = session.get(
            robots_url,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code == 200:

            rp.parse(response.text.splitlines())

            return rp, None

        rp.parse([])

        return rp, (
            f"robots.txt unavailable: HTTP {response.status_code}"
        )

    except requests.RequestException as error:

        rp.parse([])

        return rp, f"robots.txt could not be checked: {error}"


def can_fetch(rp, url):

    try:
        return rp.can_fetch(USER_AGENT, url)

    except Exception:
        return True


# ---------------------------------------------------------------------------
# Candidate deep pages
# ---------------------------------------------------------------------------

def select_answer_pages(home_soup, site_url, max_pages=2):

    if home_soup is None:
        return []

    candidates = []

    for _, href in get_featured_offerings(
        home_soup,
        site_url,
    ):

        if (
            same_domain(href, site_url)
            and normalize_url(href) != normalize_url(site_url)
        ):
            candidates.append(href)

    if len(candidates) < max_pages:

        for _, href in get_nav_links(
            home_soup,
            site_url,
        ):

            if normalize_url(href) == normalize_url(site_url):
                continue

            path = urlparse(href).path.lower()

            if any(
                hint in path
                for hint in NON_CONTENT_PATH_HINTS
            ):
                continue

            candidates.append(href)

    result = []
    seen = set()

    for candidate in candidates:

        if candidate in seen:
            continue

        seen.add(candidate)
        result.append(candidate)

        if len(result) >= max_pages:
            break

    return result


# ---------------------------------------------------------------------------
# Check 1 — Findability
# ---------------------------------------------------------------------------

def check1_findability(
    site_url,
    findings,
    unverified,
    rp,
    context,
):

    page = get_page(site_url, context)

    if (
        page["status"] is None
        or page["status"] >= 400
        or not page["html"]
    ):

        findings.append(
            make_finding(
                "issue",
                "Homepage unreachable",
                "critical",
                f"GET {site_url} failed: {status_desc(page)}",
                "Restore homepage availability before other engagement work matters.",
                [
                    "Confirm hosting/DNS is serving the homepage.",
                    "Check for a redirect or server error.",
                    "Re-run the audit once the homepage returns a successful response.",
                ],
                "critical",
            )
        )

        return None

    soup = BeautifulSoup(
        page["html"],
        "html.parser",
    )

    nav_links = get_nav_links(
        soup,
        site_url,
    )

    sub_links = get_submenu_links(
        soup,
        site_url,
    )

    offerings = get_featured_offerings(
        soup,
        site_url,
    )

    nav_hrefs = {
        normalize_url(href)
        for _, href in nav_links
    }

    sub_hrefs = {
        normalize_url(href)
        for _, href in sub_links
    }

    if not nav_links:

        findings.append(
            make_finding(
                "warning",
                "No primary navigation menu detected",
                "medium",
                f"{site_url}: no <nav>, [role=navigation], or common navigation "
                "container with anchor links was found in the crawl artifact.",
                "Add a top-level navigation menu with links to the site's main offerings.",
                [
                    "Expose primary links inside a <nav> or navigation landmark.",
                    "Ensure important homepage offerings have a corresponding navigation path.",
                    "Avoid making primary navigation dependent on client-side rendering alone.",
                ],
                "medium",
            )
        )

    else:

        unmatched = []

        for text, href in offerings[:15]:

            norm = normalize_url(href)

            in_top = norm in nav_hrefs
            in_sub = norm in sub_hrefs

            if not in_top and not in_sub:

                unmatched.append(
                    (text, href)
                )

            elif in_sub and not in_top:

                findings.append(
                    make_finding(
                        "warning",
                        f"Offering '{text}' only reachable via submenu",
                        "medium",
                        f"{site_url}: offering '{text}' links to {href}, "
                        "which appears in submenu navigation but not top-level navigation.",
                        f"Promote '{text}' to top-level navigation or make its parent category explicit.",
                        [
                            f"Add a top-level navigation path to {href}.",
                            "If submenu grouping is intentional, make the parent label descriptive.",
                            "Re-run the audit after navigation changes.",
                        ],
                        "medium",
                    )
                )

        if unmatched:

            examples = [
                f"'{text}' -> {href}"
                for text, href in unmatched[:5]
            ]

            findings.append(
                make_finding(
                    "issue",
                    "Homepage-highlighted offerings missing from navigation",
                    "critical",
                    f"{site_url}: homepage-linked offerings have no matching "
                    f"top-level or submenu navigation link: {examples}.",
                    "Add navigation paths for important homepage-highlighted offerings.",
                    [
                        "Cross-reference homepage offering URLs against navigation targets.",
                        "Add a top-level or submenu link to every unmatched offering.",
                        "Re-run the crawl to confirm each offering is reachable through navigation.",
                    ],
                    "critical",
                )
            )

        vague_found = [
            text
            for text, _ in nav_links
            if text.strip().lower() in GENERIC_LABELS
        ]

        if vague_found:

            findings.append(
                make_finding(
                    "warning",
                    "Vague top-level navigation labels",
                    "medium",
                    f"{site_url}: navigation contains vague labels {vague_found}.",
                    "Rename vague labels to describe what the visitor will find.",
                    [
                        "Replace generic labels such as 'More' with meaningful category names.",
                        "Keep labels short but descriptive.",
                        "Verify that labels match the destination page's purpose.",
                    ],
                    "medium",
                )
            )

    # Validate a small number of nav targets.
    #
    # If crawlability already visited the target, this uses that result.
    # It NEVER performs another request for an already-crawled page.
    dead_nav = []

    checked = 0

    for text, href in nav_links:

        if checked >= 3:
            break

        if not same_domain(href, site_url):
            continue

        if context.enabled:

            target = context.get(href)

            if target is None:
                continue

            target_page = get_page(
                href,
                context,
            )

        else:

            if not can_fetch(rp, href):
                continue

            target_page = get_page(
                href,
                context,
            )

        checked += 1

        if (
            target_page["status"] is None
            or target_page["status"] >= 400
        ):

            dead_nav.append(
                (
                    text,
                    href,
                    status_desc(target_page),
                )
            )

        elif (
            target_page["html"]
            and len(
                BeautifulSoup(
                    target_page["html"],
                    "html.parser",
                ).get_text(strip=True)
            ) < 150
        ):

            dead_nav.append(
                (
                    text,
                    href,
                    "content too thin (<150 chars visible text)",
                )
            )

    for text, href, reason in dead_nav:

        findings.append(
            make_finding(
                "issue",
                f"Nav item '{text}' leads to a broken or empty page",
                "high",
                f"{site_url} nav link '{text}' -> {href}: {reason}.",
                f"Fix or remove the '{text}' navigation link.",
                [
                    f"Restore the page at {href} if it should exist.",
                    "If deprecated, redirect it to a live replacement or remove the nav item.",
                    "Re-test the navigation target after the change.",
                ],
                "high",
            )
        )

    if not any(
        f["title"].startswith(
            (
                "No primary",
                "Homepage-highlighted",
                "Nav item",
            )
        )
        for f in findings
    ):

        findings.append(
            make_finding(
                "opportunity",
                "Consider grouping related offerings under shared nav categories",
                "low",
                f"{site_url}: navigation and homepage offerings are consistent; "
                "no findability defect was detected.",
                "Evaluate whether related offerings could be grouped to improve scanning.",
                [
                    "Review the current number of top-level navigation items.",
                    "Group closely related offerings where that improves comprehension.",
                    "Re-test navigation after any restructuring.",
                ],
                "low",
            )
        )

    return soup


# ---------------------------------------------------------------------------
# Check 2 — Deep-entry orientation
# ---------------------------------------------------------------------------

def check2_orientation(
    entry_pages,
    home_soup,
    site_url,
    findings,
    unverified,
    context,
):

    auto_selected = False

    if not entry_pages:

        entry_pages = select_answer_pages(
            home_soup,
            site_url,
        )

        auto_selected = True

    if not entry_pages:

        unverified.append(
            {
                "check": "check2_orientation",
                "reason": (
                    "no entry pages were provided and no candidate answer "
                    "pages could be selected from the homepage"
                ),
            }
        )

        return

    for url in entry_pages:

        if "/fragments/" in url:
            continue

        page = get_page(
            url,
            context,
        )

        # With an orchestrator crawl, do not silently fetch a page that was
        # not part of that crawl. Mark it unverified instead.
        if (
            context.enabled
            and context.get(url) is None
        ):

            unverified.append(
                {
                    "check": "check2_orientation",
                    "url": url,
                    "reason": (
                        "candidate deep-entry page was not present in the "
                        "crawlability artifact; engagement audit did not "
                        "perform a second navigation request"
                    ),
                }
            )

            continue

        if (
            page["status"] is None
            or page["status"] >= 400
            or not page["html"]
        ):

            findings.append(
                make_finding(
                    "issue",
                    f"Entry page unreachable: {url}",
                    "high",
                    f"GET {url} failed: {status_desc(page)}"
                    + (
                        " (auto-selected as a likely answer page)"
                        if auto_selected
                        else ""
                    ),
                    "Fix the broken entry page since assistant-referred visitors may land here directly.",
                    [
                        "Confirm the URL is valid and not a stale path.",
                        "Restore the page or redirect it to the closest relevant replacement.",
                        "Re-test direct access to the URL.",
                    ],
                    "high",
                )
            )

            continue

        soup = BeautifulSoup(
            page["html"],
            "html.parser",
        )

        has_breadcrumb = bool(
            soup.select(
                '[class*=breadcrumb], '
                '[aria-label*=breadcrumb i], '
                'nav[aria-label*=breadcrumb i]'
            )
        )

        has_parent_link = bool(
            soup.select(
                'a[rel="up"], '
                'a[class*=parent], '
                'a[class*=back]'
            )
        )

        orientation_cues = (
            has_breadcrumb
            or has_parent_link
        )

        clean_text = strip_boilerplate_text(
            soup
        )

        h1 = soup.find("h1")

        self_explanatory = (
            bool(
                h1
                and h1.get_text(strip=True)
            )
            and len(clean_text) > 300
        )

        main_area = soup.find("main") or soup

        chrome_links = set(
            main_area.select(
                "nav a, footer a"
            )
        )

        next_step_links = [
            a
            for a in main_area.find_all(
                "a",
                href=True,
            )
            if a not in chrome_links
        ]

        has_cta_or_related = (
            len(next_step_links) > 2
        )

        if not orientation_cues and not self_explanatory:
            severity = "critical"

        elif not orientation_cues:
            severity = "high"

        elif not has_cta_or_related:
            severity = "medium"

        else:
            severity = None

        tag = (
            " (auto-selected as a likely answer page)"
            if auto_selected
            else ""
        )

        if severity in ("critical", "high"):

            findings.append(
                make_finding(
                    "issue",
                    f"No orientation cues on deep-linked page: {url}",
                    severity,
                    f"{url}{tag}: no breadcrumb or parent-link element found; "
                    + (
                        "page also lacks a clear <h1> or has <300 characters "
                        "of non-chrome body text."
                        if severity == "critical"
                        else
                        "page content is otherwise self-explanatory."
                    ),
                    "Add orientation cues so visitors arriving directly from an assistant are not lost.",
                    [
                        "Add a breadcrumb trail showing the page's position in the site hierarchy.",
                        "Ensure the page has a clear <h1> and enough standalone explanatory text.",
                        "Link explicitly to the relevant parent category or section.",
                    ],
                    severity,
                )
            )

        elif severity == "medium":

            findings.append(
                make_finding(
                    "warning",
                    f"No clear next step on deep-linked page: {url}",
                    "medium",
                    f"{url}{tag}: orientation cues are present, but only "
                    f"{len(next_step_links)} non-navigation content links were found.",
                    "Add a clear next action or related-content path.",
                    [
                        "Add a CTA relevant to the page's purpose.",
                        "Add 2–3 related-content or next-step links.",
                        "Avoid ending the visitor journey immediately after the content.",
                    ],
                    "medium",
                )
            )

        else:

            findings.append(
                make_finding(
                    "opportunity",
                    f"Consider referral-aware content on {url}",
                    "low",
                    f"{url}{tag}: orientation, self-explanatory content, and next steps are present.",
                    "Strengthen the page for visitors arriving from an AI assistant.",
                    [
                        "Add a short framing sentence that works without homepage context.",
                        "Surface likely follow-up questions or related actions.",
                        "Keep the page's context and navigation current.",
                    ],
                    "low",
                )
            )


# ---------------------------------------------------------------------------
# Check 3 — Link health / dead ends
# ---------------------------------------------------------------------------

def check3_link_crawl(
    site_url,
    home_soup,
    findings,
    unverified,
    rp,
    context,
):
    """
    IMPORTANT:

    With crawlability artifacts available, this function does NOT crawl.

    It analyzes the pages already collected by crawlability and compares
    links between those pages against the collected HTTP statuses.

    Links whose targets were not crawled are explicitly marked unverified
    rather than causing another network crawl.
    """

    if context.enabled:

        pages = context.all_pages()

        if not pages:

            unverified.append(
                {
                    "check": "check3_link_crawl",
                    "reason": "crawlability returned no page artifacts",
                }
            )

            return

        known_status = {}

        for page in pages:

            requested = page.get("url")
            final_url = page.get("finalUrl")

            status = page.get("status")

            for candidate in (
                requested,
                final_url,
            ):

                if candidate:

                    known_status[
                        normalize_url(
                            strip_fragment(candidate)
                        )
                    ] = status

        broken = {}
        unknown_targets = set()

        page_link_counts = {}

        for page in pages:

            page_url = (
                page.get("finalUrl")
                or page.get("url")
            )

            html = page.get("html")

            if not page_url or not html:
                continue

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            body_links = []

            for anchor in soup.find_all(
                "a",
                href=True,
            ):

                target = urljoin(
                    page_url,
                    anchor["href"],
                )

                target = strip_fragment(
                    target
                )

                if not same_domain(
                    target,
                    site_url,
                ):
                    continue

                body_links.append(
                    target
                )

                target_key = normalize_url(
                    target
                )

                if target_key in known_status:

                    status = known_status[
                        target_key
                    ]

                    if (
                        status is None
                        or status >= 400
                    ):

                        broken[
                            target_key
                        ] = status

                else:

                    unknown_targets.add(
                        target_key
                    )

            chrome_targets = {
                normalize_url(
                    strip_fragment(
                        urljoin(
                            page_url,
                            a["href"],
                        )
                    )
                )
                for a in soup.select(
                    "nav a[href], footer a[href], header a[href]"
                )
            }

            outlinks_beyond_chrome = [
                link
                for link in body_links
                if normalize_url(link)
                not in chrome_targets
            ]

            clean_text_len = len(
                strip_boilerplate_text(
                    soup
                )
            )

            page_link_counts[
                normalize_url(page_url)
            ] = (
                len(outlinks_beyond_chrome) > 0,
                clean_text_len > 250,
            )

        # Report known broken links.
        home_links = set()

        if home_soup is not None:

            for anchor in home_soup.find_all(
                "a",
                href=True,
            ):

                target = urljoin(
                    site_url,
                    anchor["href"],
                )

                if same_domain(
                    target,
                    site_url,
                ):

                    home_links.add(
                        normalize_url(
                            strip_fragment(target)
                        )
                    )

        for url, status in list(
            broken.items()
        )[:10]:

            severity = (
                "critical"
                if url in home_links
                else "high"
            )

            findings.append(
                make_finding(
                    "issue",
                    "Broken internal link",
                    severity,
                    f"{url} returned "
                    f"{status if status is not None else 'an error'} "
                    f"in the crawlability artifact.",
                    f"Fix or remove the internal link to {url}.",
                    [
                        f"Restore {url} if it should exist.",
                        "If retired, redirect it to the closest relevant live page.",
                        "Update or remove internal links pointing to the broken target.",
                    ],
                    severity,
                )
            )

        # Dead ends are evaluated only on pages crawlability actually saw.
        dead_ends = [
            url
            for url, (
                has_outlinks,
                has_content,
            )
            in page_link_counts.items()
            if not has_outlinks
            and not has_content
        ]

        for url in dead_ends[:10]:

            findings.append(
                make_finding(
                    "issue",
                    "Dead-end page with no outlinks or substantive content",
                    "medium",
                    f"{url}: page loaded successfully but has no outlinks "
                    "beyond navigation/header/footer and fewer than 250 "
                    "characters of visible text after boilerplate removal.",
                    "Give the page substantive content or a path forward.",
                    [
                        "Add page-specific content if this is a real destination.",
                        "Add related or next-step links if visitors should continue.",
                        "Remove or redirect the page if it serves no useful purpose.",
                    ],
                    "medium",
                )
            )

        if unknown_targets:

            # Do NOT crawl these. This is exactly what prevents the
            # engagement skill from becoming a second crawler.
            unverified.append(
                {
                    "check": "check3_link_crawl",
                    "reason": (
                        f"{len(unknown_targets)} same-domain link target(s) "
                        "were not present in the crawlability artifact; "
                        "their status was not independently requested by "
                        "engagement-audit"
                    ),
                }
            )

        return

    # ------------------------------------------------------------------
    # Standalone fallback.
    #
    # This path preserves the ability to execute:
    #
    #   python engagement_audit.py https://example.com
    #
    # outside the orchestrator.
    # ------------------------------------------------------------------

    visited = set()
    link_status = {}
    page_link_counts = {}

    def crawl_page(url):

        url = strip_fragment(url)

        if (
            url in visited
            or len(visited) >= MAX_CRAWL_PAGES
        ):
            return None

        if not same_domain(
            url,
            site_url,
        ):
            return None

        if not can_fetch(
            rp,
            url,
        ):
            return None

        visited.add(url)

        page = get_page(
            url,
            context,
        )

        link_status[url] = (
            page["status"]
            if page["status"] is not None
            else page["error"]
        )

        if (
            page["status"] is None
            or page["status"] >= 400
            or not page["html"]
        ):
            return None

        soup = BeautifulSoup(
            page["html"],
            "html.parser",
        )

        links = []

        for anchor in soup.find_all(
            "a",
            href=True,
        ):

            target = strip_fragment(
                urljoin(
                    url,
                    anchor["href"],
                )
            )

            if same_domain(
                target,
                site_url,
            ):
                links.append(target)

        chrome = {
            strip_fragment(
                urljoin(
                    url,
                    anchor["href"],
                )
            )
            for anchor in soup.select(
                "nav a[href], footer a[href], header a[href]"
            )
        }

        outlinks = [
            link
            for link in links
            if link not in chrome
        ]

        page_link_counts[url] = (
            bool(outlinks),
            len(
                strip_boilerplate_text(
                    soup
                )
            ) > 250,
        )

        return soup, links

    crawl_page(site_url)

    nav_targets = []

    if home_soup is not None:

        for _, href in get_nav_links(
            home_soup,
            site_url,
        ):

            clean = strip_fragment(
                href
            )

            if (
                same_domain(
                    clean,
                    site_url,
                )
                and clean not in nav_targets
            ):
                nav_targets.append(clean)

    level1_children = []

    for nav_url in nav_targets:

        if len(visited) >= MAX_CRAWL_PAGES:
            break

        result = crawl_page(
            nav_url
        )

        if result:

            _, links = result

            level1_children.extend(
                link
                for link in links
                if same_domain(
                    link,
                    site_url,
                )
            )

    for child_url in level1_children:

        if len(visited) >= MAX_CRAWL_PAGES:
            break

        crawl_page(child_url)

    broken = {
        url: status
        for url, status in link_status.items()
        if (
            isinstance(status, int)
            and status >= 400
        )
        or isinstance(status, str)
    }

    for url, status in list(
        broken.items()
    )[:10]:

        findings.append(
            make_finding(
                "issue",
                "Broken internal link",
                "high",
                f"{url} returned {status} during engagement crawl of {site_url}.",
                f"Fix or remove the link to {url}.",
                [
                    f"Restore {url} if it should exist.",
                    "Redirect retired URLs to the closest relevant live page.",
                    "Update or remove internal links pointing to it.",
                ],
                "high",
            )
        )

    dead_ends = [
        url
        for url, (
            has_outlinks,
            has_content,
        )
        in page_link_counts.items()
        if not has_outlinks
        and not has_content
    ]

    for url in dead_ends[:10]:

        findings.append(
            make_finding(
                "issue",
                "Dead-end page with no outlinks or substantive content",
                "medium",
                f"{url}: page loaded successfully but has no useful outlinks "
                "and fewer than 250 characters of visible text.",
                "Give the page substantive content or a path forward.",
                [
                    "Add substantive page-specific content.",
                    "Add related or next-step links.",
                    "Remove or redirect the page if it serves no useful purpose.",
                ],
                "medium",
            )
        )


# ---------------------------------------------------------------------------
# Check 4 — Static mobile readiness
# ---------------------------------------------------------------------------

def check4_mobile(
    site_url,
    home_soup,
    findings,
):

    if home_soup is None:
        return

    viewport = home_soup.find(
        "meta",
        attrs={
            "name": "viewport"
        },
    )

    if not viewport:

        findings.append(
            make_finding(
                "issue",
                "No viewport meta tag",
                "medium",
                f"{site_url}: no <meta name=\"viewport\"> tag found.",
                "Add a responsive viewport meta tag.",
                [
                    'Add <meta name="viewport" content="width=device-width, initial-scale=1">.',
                    "Ensure it is present in server-rendered HTML.",
                    "Verify the page on a real mobile viewport.",
                ],
                "medium",
            )
        )

    else:

        content = viewport.get(
            "content",
            "",
        )

        if "width=device-width" not in content:

            findings.append(
                make_finding(
                    "warning",
                    "Viewport meta tag present but not device-width",
                    "medium",
                    f"{site_url}: viewport content is '{content}'.",
                    "Update the viewport tag to use device-width scaling.",
                    [
                        'Set content="width=device-width, initial-scale=1".',
                        "Avoid fixed pixel viewport widths.",
                        "Re-test on a narrow viewport.",
                    ],
                    "medium",
                )
            )

    fixed_width_hits = []

    for tag in home_soup.find_all(
        style=True
    ):

        match = re.search(
            r"width:\s*(\d+)px",
            tag["style"],
        )

        if (
            match
            and int(match.group(1))
            > MOBILE_VIEWPORT_WIDTH
        ):

            fixed_width_hits.append(
                (
                    tag.name,
                    match.group(1),
                )
            )

    for style_tag in home_soup.find_all(
        "style"
    ):

        for match in re.finditer(
            r"width:\s*(\d+)px",
            style_tag.get_text(),
        ):

            if (
                int(match.group(1))
                > MOBILE_VIEWPORT_WIDTH
            ):

                fixed_width_hits.append(
                    (
                        "<style> block",
                        match.group(1),
                    )
                )

    if fixed_width_hits:

        findings.append(
            make_finding(
                "warning",
                "Fixed-width elements exceeding mobile viewport",
                "medium",
                f"{site_url}: found {len(fixed_width_hits)} fixed widths "
                f"greater than {MOBILE_VIEWPORT_WIDTH}px, e.g. "
                f"{fixed_width_hits[:5]}.",
                "Replace fixed pixel widths with responsive layout rules.",
                [
                    "Use percentage, max-width, Grid, or Flexbox-based sizing.",
                    "Add a mobile breakpoint where necessary.",
                    "Re-test the page on narrow screens.",
                ],
                "medium",
            )
        )


# ---------------------------------------------------------------------------
# Check 5 — Performance signals
# ---------------------------------------------------------------------------

def check5_performance(
    site_url,
    findings,
    context,
    unverified,
):

    page = get_page(
        site_url,
        context,
    )

    if (
        page["status"] is None
        or not page["html"]
    ):
        return

    payload_kb = len(
        page["html"].encode("utf-8")
    ) / 1024

    soup = BeautifulSoup(
        page["html"],
        "html.parser",
    )

    head = soup.find("head") or soup

    blocking = head.find_all(
        "script",
        src=True,
    )

    blocking = [
        script
        for script in blocking
        if not script.get("async")
        and not script.get("defer")
    ]

    blocking += head.find_all(
        "link",
        rel="stylesheet",
    )

    # When crawlability supplied the page, we deliberately do not perform
    # another navigation request just to measure response time.
    elapsed = page.get("elapsed")

    if elapsed is None:

        if context.enabled:

            unverified.append(
                {
                    "check": "check5_performance_response_time",
                    "reason": (
                        "crawlability supplied the page HTML but did not "
                        "provide navigation timing; engagement-audit did "
                        "not issue a duplicate homepage request"
                    ),
                }
            )

    slow = (
        elapsed is not None
        and elapsed >= SLOW_RESPONSE_SECONDS
    )

    borderline_slow = (
        elapsed is not None
        and elapsed >= ACCEPTABLE_RESPONSE_SECONDS
    )

    heavy = (
        payload_kb > 1500
        or len(blocking) > 10
    )

    severity = None

    if slow and heavy:
        severity = "critical"

    elif slow:
        severity = "high"

    elif heavy:
        severity = "medium"

    if severity:

        timing_text = (
            f"{elapsed:.2f}s"
            if elapsed is not None
            else "not measured from the existing crawl artifact"
        )

        findings.append(
            make_finding(
                "issue"
                if severity in ("critical", "high")
                else "warning",
                "Slow or heavy initial page load",
                severity,
                f"{site_url}: response time {timing_text}, "
                f"HTML payload {payload_kb:.0f}KB, "
                f"{len(blocking)} synchronous script/stylesheet tag(s) "
                "in <head>.",
                "Reduce initial response and render-blocking work.",
                [
                    "Defer non-critical scripts.",
                    "Reduce render-blocking CSS.",
                    "Compress and appropriately size initial assets.",
                    "Use server caching/CDN delivery where appropriate.",
                ],
                severity,
            )
        )

    elif borderline_slow:

        findings.append(
            make_finding(
                "opportunity",
                "Response time is borderline",
                "low",
                f"{site_url}: response time was {elapsed:.2f}s.",
                "Consider proactive performance improvements.",
                [
                    "Profile server response time under representative load.",
                    "Review caching/CDN configuration.",
                    "Re-measure as the page grows.",
                ],
                "low",
            )
        )

    # Image size checks are still safe because these are resource-level HEAD
    # requests, not a second page crawl.
    large_images = []

    for img in soup.find_all(
        "img",
        src=True,
    )[:15]:

        img_url = urljoin(
            site_url,
            img["src"],
        )

        try:

            response = session.head(
                img_url,
                timeout=5,
                allow_redirects=True,
            )

            size = response.headers.get(
                "Content-Length"
            )

            if (
                size
                and int(size) > 500_000
            ):

                large_images.append(
                    (
                        img_url,
                        int(size),
                    )
                )

        except requests.RequestException:
            continue

    if large_images:

        examples = [
            (
                url,
                f"{size / 1024:.0f}KB",
            )
            for url, size
            in large_images[:5]
        ]

        findings.append(
            make_finding(
                "warning",
                "Unusually large image resources on homepage",
                "medium",
                f"{site_url}: {len(large_images)} image(s) over 500KB, "
                f"e.g. {examples}.",
                "Compress and appropriately size homepage images.",
                [
                    "Resize and compress oversized images.",
                    "Serve modern formats such as WebP/AVIF where appropriate.",
                    "Lazy-load below-the-fold images.",
                ],
                "medium",
            )
        )


# ---------------------------------------------------------------------------
# Check 6 — Search
# ---------------------------------------------------------------------------

def check6_search(
    site_url,
    home_soup,
    findings,
    unverified,
):

    if home_soup is None:
        return

    search_input = home_soup.select_one(
        'input[type="search"], '
        '[role="search"], '
        'form[action*=search], '
        'input[name*=search i]'
    )

    if not search_input:

        offerings = get_featured_offerings(
            home_soup,
            site_url,
        )

        if len(offerings) > 8:

            findings.append(
                make_finding(
                    "opportunity",
                    "No on-site search on a content-heavy site",
                    "medium",
                    f"{site_url}: no search input or search form detected; "
                    f"homepage exposes {len(offerings)} featured offerings.",
                    "Add on-site search for visitors looking for specific content.",
                    [
                        "Add a search input backed by an internal search index.",
                        "Ensure search result pages are crawlable.",
                        "Expose search prominently in the header or navigation.",
                    ],
                    "medium",
                )
            )

        return

    form = (
        search_input
        if search_input.name == "form"
        else search_input.find_parent("form")
    )

    if (
        form
        and form.get("method", "get").lower() == "get"
        and form.get("action")
    ):

        action = urljoin(
            site_url,
            form["action"],
        )

        query_param = None

        for inp in form.find_all(
            "input"
        ):

            if inp.get("type") in (
                None,
                "text",
                "search",
            ):

                query_param = inp.get(
                    "name"
                )

                break

        if not query_param:

            unverified.append(
                {
                    "check": "check6_search_quality",
                    "reason": (
                        "search form found but no identifiable query "
                        "parameter was available for a safe GET test"
                    ),
                }
            )

            return

        candidates = guess_query_terms(
            home_soup
        )

        if not candidates:

            unverified.append(
                {
                    "check": "check6_search_quality",
                    "reason": (
                        "search endpoint found, but no plausible query "
                        "term could be derived safely from site content"
                    ),
                }
            )

            return

        query_term = candidates[0]

        test_url = (
            f"{action}"
            f"?{query_param}="
            f"{quote(query_term)}"
        )

        # Search testing is not a crawl. It is a single explicit GET test
        # against the site's declared search endpoint.
        response = fetch_live(
            test_url
        )

        if (
            response["status"] is None
            or response["status"] >= 400
        ):

            findings.append(
                make_finding(
                    "issue",
                    "Site search endpoint errors on a plausible query",
                    "high",
                    f"GET {test_url} using query term '{query_term}' "
                    f"returned {status_desc(response)}.",
                    "Fix the search endpoint so plausible queries return results.",
                    [
                        "Reproduce the error with the same query.",
                        "Verify the GET parameter matches the form's contract.",
                        "Re-test with several terms known to exist on the site.",
                    ],
                    "high",
                )
            )

        else:

            result_soup = BeautifulSoup(
                response["html"] or "",
                "html.parser",
            )

            result_text = (
                result_soup
                .get_text(strip=True)
                .lower()
            )

            no_results_markers = [
                "no results",
                "0 results",
                "nothing found",
                "no matches",
            ]

            looks_empty = any(
                marker in result_text
                for marker in no_results_markers
            )

            if looks_empty:

                findings.append(
                    make_finding(
                        "warning",
                        "Site search returns no results for a plausible query",
                        "high",
                        f"GET {test_url} returned a 'no results' style message "
                        f"for query '{query_term}', derived from site content.",
                        "Verify that the search index covers current site content.",
                        [
                            "Test additional terms known to appear verbatim on the site.",
                            "Check whether the search index is stale or incorrectly scoped.",
                            "Refresh or rebuild the search index if necessary.",
                        ],
                        "high",
                    )
                )

    else:

        unverified.append(
            {
                "check": "check6_search_quality",
                "reason": (
                    "search UI detected but no safe GET endpoint could "
                    "be identified without submitting a form"
                ),
            }
        )

        findings.append(
            make_finding(
                "opportunity",
                "On-site search present (quality unverified)",
                "low",
                f"{site_url}: search UI detected, but its endpoint could "
                "not be safely tested read-only.",
                "Manually verify search result relevance.",
                [
                    "Test representative search queries manually.",
                    "Confirm results are relevant and current.",
                    "Expose a GET-based search interface if automated testing is desired.",
                ],
                "low",
            )
        )


# ---------------------------------------------------------------------------
# Main audit entrypoint
# ---------------------------------------------------------------------------

def run_audit(
    site_url,
    entry_pages=None,
    crawl_audit=None,
):
    """
    Run the engagement audit.

    crawl_audit:
        Optional result produced by crawlability.

        When supplied, engagement reuses those pages instead of crawling
        the website again.

    This is the interface used by audit-orchestrator.
    """

    global _finding_counter
    _finding_counter = 0

    findings = []
    unverified = []

    context = CrawlContext(
        crawl_audit
    )

    # ---------------------------------------------------------------
    # Robots
    # ---------------------------------------------------------------
    #
    # Crawlability already handled robots.txt when a crawl artifact is
    # supplied. Do not request it again.
    #
    if context.enabled:

        rp = None

        blocked_count = len(
            context.blocked_urls
        )

        if blocked_count:

            unverified.append(
                {
                    "check": "robots",
                    "reason": (
                        f"{blocked_count} URL(s) were excluded by the "
                        "crawlability crawler's robots.txt rules"
                    ),
                }
            )

    else:

        rp, robots_issue = load_robots(
            site_url
        )

        if robots_issue:

            unverified.append(
                {
                    "check": "robots",
                    "reason": robots_issue,
                }
            )

    # ---------------------------------------------------------------
    # Run checks
    # ---------------------------------------------------------------

    home_soup = check1_findability(
        site_url,
        findings,
        unverified,
        rp,
        context,
    )

    check2_orientation(
        entry_pages or [],
        home_soup,
        site_url,
        findings,
        unverified,
        context,
    )

    check3_link_crawl(
        site_url,
        home_soup,
        findings,
        unverified,
        rp,
        context,
    )

    check4_mobile(
        site_url,
        home_soup,
        findings,
    )

    check5_performance(
        site_url,
        findings,
        context,
        unverified,
    )

    check6_search(
        site_url,
        home_soup,
        findings,
        unverified,
    )

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    for finding in findings:

        severity = finding.get(
            "severity"
        )

        if severity in counts:
            counts[severity] += 1

    return {
        "site": site_url,
        "audited_at": datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "summary": {
            "total_findings": len(findings),
            **counts,
        },
        "findings": findings,
        "unverified_checks": unverified,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run the engagement audit against a site."
        )
    )

    parser.add_argument(
        "site_url",
        help="Homepage URL of the site to audit",
    )

    parser.add_argument(
        "--entry-pages",
        nargs="*",
        default=[],
        help=(
            "Deep-page URLs to test for orientation. "
            "If omitted, 1-2 are selected automatically."
        ),
    )

    args = parser.parse_args()

    report = run_audit(
        args.site_url,
        args.entry_pages,
    )

    print(
        json.dumps(
            report,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()