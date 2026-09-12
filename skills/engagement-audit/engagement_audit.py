#!/usr/bin/env python3
"""
engagement_audit.py

Implements the engagement-audit skill's checks against a live site using
static HTTP/HTML inspection only (no rendering). Read-only. Respects
robots.txt. Produces a findings list in the marketplace's fixed report
schema, to be merged by the audit-orchestrator entrypoint.

Scope: this skill owns on-site engagement -- findability, deep-entry
orientation, dead ends, static mobile readiness, initial performance, and
search quality. Sitemap/orphan-page detection and generic accessibility
checks (alt text, heading structure) are intentionally NOT implemented here
to avoid overlapping with the crawlability and non-text/structured-data
skills owned elsewhere in this marketplace.

Usage:
    python engagement_audit.py https://example.com \
        --entry-pages https://example.com/some-deep-page https://example.com/another

Output: JSON printed to stdout, matching:
{
  "site": "...",
  "audited_at": "...",
  "summary": {"total_findings": N, "critical": N, "high": N, "medium": N, "low": N},
  "findings": [ {id, type, title, severity, evidence, suggested_action}, ... ],
  "unverified_checks": [ {check, reason}, ... ]
}
"""

import argparse
import json
import re
import time
from collections import deque
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

NON_CONTENT_PATH_HINTS = ("about", "contact", "privacy", "terms", "login",
                           "signin", "sign-in", "signup", "sign-up", "cart",
                           "checkout", "account")
GENERIC_LABELS = {"home", "menu", "more", "other", "misc", "info", "page",
                   "about", "contact", "login", "sign in", "sign up", "cart"}

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

_finding_counter = 0


def next_id():
    global _finding_counter
    _finding_counter += 1
    return f"F-eng-{_finding_counter:03d}"


def make_finding(type_, title, severity, evidence, summary, steps, priority):
    return {
        "id": next_id(),
        "type": type_,
        "title": title,
        "severity": severity,
        "evidence": evidence,
        "suggested_action": {
            "summary": summary,
            "steps": steps,
            "priority": priority,
        },
    }


def same_domain(url_a, url_b):
    return urlparse(url_a).netloc == urlparse(url_b).netloc


def normalize_url(url):
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def fetch(url, allow_redirects=True):
    """Returns (response_or_None, elapsed_seconds, error_str_or_None).

    IMPORTANT: requests.Response.__bool__ returns False for any 4xx/5xx
    status code (it reflects `.ok`, not "did we get a response"). Every
    caller MUST check `resp is None` explicitly to detect a failed request
    -- never `if resp` / `if not resp` -- or a real error response (e.g.
    HTTP 404) gets silently treated as if no response was received at all.
    """
    try:
        start = time.monotonic()
        resp = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=allow_redirects)
        elapsed = time.monotonic() - start
        return resp, elapsed, None
    except requests.RequestException as e:
        return None, None, str(e)


def status_desc(resp, err):
    if err:
        return err
    return f"HTTP {resp.status_code if resp is not None else 'unknown'}"


def load_robots(site_url):
    """Returns (RobotFileParser, issue_or_None).

    A missing/unfetchable robots.txt is treated as allow-all for crawling
    purposes (standard behavior), but the caller must still be told when
    this happened via the returned issue string, so it can be recorded as
    an unverified check rather than silently indistinguishable from a
    successfully-fetched robots.txt with no restrictions.
    """
    robots_url = urljoin(site_url, "/robots.txt")
    rp = RobotFileParser()
    try:
        resp, _, err = fetch(robots_url)
        if resp is not None and resp.status_code == 200:
            rp.parse(resp.text.splitlines())
            return rp, None
        rp.parse([])
        return rp, f"robots.txt unavailable: {status_desc(resp, err)}"
    except Exception as e:
        rp.parse([])
        return rp, f"robots.txt could not be checked: {e}"


def can_fetch(rp, url):
    try:
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


def strip_boilerplate_text(soup):
    copy = BeautifulSoup(str(soup), "html.parser")
    for tag in copy.select("nav, footer, header"):
        tag.decompose()
    return copy.get_text(separator=" ", strip=True)


def get_nav_links(soup, base_url):
    nav_candidates = soup.select('nav, [role="navigation"], header nav, .nav, .navbar, .menu')
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
        'nav ul ul a[href], nav .submenu a[href], nav .dropdown-menu a[href], '
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
    """Homepage-highlighted offerings, as (text, absolute_href) pairs.

    An "offering" must have an associated link (its own <a>, or a link
    findable within its immediate card/section container) -- a plain,
    unlinked heading is a section label, not something a visitor could
    navigate to, so it can't sensibly be flagged as "missing from nav."

    Headings inside <footer> are excluded: footer section headers (e.g.
    "About Us", "Contributing") are organizational labels for footer link
    groups, not homepage-highlighted offerings -- comparing them against
    the primary nav produced false positives on sites like pypi.org.

    Visually-hidden headings are excluded regardless of location: a common
    accessibility pattern is a visually-hidden <h2>/<h3> that exists purely
    to label a landmark region for screen readers (e.g. class names like
    "visually-hidden", "sr-only", "visuallyHidden"). These are never seen
    by a sighted visitor and aren't "offerings" a visitor would look for in
    the nav -- including one (e.g. a hidden "Navigation Menu" label inside
    <header>) produced a false positive against github.com during testing.

    <h1> is excluded: on a homepage it's typically the site/brand title or
    hero tagline, not a specific offering.
    """
    offerings = []
    seen = set()

    footer_headings = set()
    for footer in soup.find_all("footer"):
        footer_headings.update(id(h) for h in footer.find_all(["h1", "h2", "h3"]))

    hidden_pattern = re.compile(r"visually.?hidden|sr.?only|screen.?reader", re.IGNORECASE)

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
        parent = tag.find_parent(["div", "section", "li", "article", "a"])
        if parent is not None:
            if parent.name == "a" and parent.get("href"):
                return parent["href"]
            a2 = parent.find("a", href=True)
            if a2:
                return a2["href"]
        return None

    for tag in soup.select("h2, h3"):
        if id(tag) in footer_headings or is_visually_hidden(tag):
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

    for tag in soup.select("[class*=feature] a[href], [class*=category] a[href], "
                            "[class*=highlight] a[href]"):
        if tag.find_parent("footer") is not None or is_visually_hidden(tag):
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
    for tag in soup.select("nav a, h2, h3, [class*=feature] a, [class*=category] a"):
        if tag.find_parent("footer") is not None:
            continue
        text = tag.get_text(strip=True)
        if text and 2 <= len(text) <= 30 and text.lower() not in GENERIC_LABELS:
            candidates.append(text.split()[0])
    seen = set()
    unique = []
    for c in candidates:
        if c.lower() not in seen:
            seen.add(c.lower())
            unique.append(c)
    unique.sort(key=len)
    return unique


def select_answer_pages(home_soup, site_url, max_pages=2):
    if home_soup is None:
        return []
    candidates = []
    for text, href in get_featured_offerings(home_soup, site_url):
        if same_domain(href, site_url) and normalize_url(href) != normalize_url(site_url):
            candidates.append(href)
    if len(candidates) < max_pages:
        for text, href in get_nav_links(home_soup, site_url):
            if normalize_url(href) == normalize_url(site_url):
                continue
            path = urlparse(href).path.lower()
            if any(hint in path for hint in NON_CONTENT_PATH_HINTS):
                continue
            candidates.append(href)
    seen = set()
    result = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            result.append(c)
        if len(result) >= max_pages:
            break
    return result


def check1_findability(site_url, findings, unverified, rp):
    resp, elapsed, err = fetch(site_url)
    if resp is None or resp.status_code != 200:
        findings.append(make_finding(
            "issue", "Homepage unreachable", "critical",
            f"GET {site_url} failed: {status_desc(resp, err)}",
            "Restore homepage availability before any other findability work matters.",
            ["Confirm hosting/DNS is serving the homepage.",
             "Check for a misconfigured redirect or server error.",
             "Re-run this audit once the homepage returns HTTP 200."],
            "critical",
        ))
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    nav_links = get_nav_links(soup, site_url)
    sub_links = get_submenu_links(soup, site_url)
    offerings = get_featured_offerings(soup, site_url)

    nav_hrefs = {normalize_url(href) for _, href in nav_links}
    sub_hrefs = {normalize_url(href) for _, href in sub_links}

    if not nav_links:
        findings.append(make_finding(
            "warning", "No primary navigation menu detected", "medium",
            f"{site_url}: no <nav>, [role=navigation], or common nav-class container "
            f"with anchor links was found in the fetched HTML.",
            "Add a top-level navigation menu with links to the site's main offerings/categories.",
            ["Wrap primary links in a <nav> or role=\"navigation\" landmark so both crawlers "
             "and assistive tech can identify it as navigation.",
             "Ensure every top-level offering shown on the homepage has a corresponding link "
             "inside that landmark.",
             "Avoid nav rendered purely via client-side JS with no server-rendered fallback, "
             "since this skill (and many crawlers) only see static HTML."],
            "medium",
        ))
    else:
        unmatched = []
        for text, href in offerings[:15]:
            norm = normalize_url(href)
            in_top = norm in nav_hrefs
            in_sub = norm in sub_hrefs
            if not in_top and not in_sub:
                unmatched.append((text, href))
            elif in_sub and not in_top:
                findings.append(make_finding(
                    "warning", f"Offering '{text}' only reachable via submenu", "medium",
                    f"{site_url}: offering '{text}' links to {href}, which matches a "
                    f"submenu link but no top-level nav entry.",
                    f"Promote '{text}' to the top-level nav or add a direct top-level link.",
                    [f"Add a top-level nav item pointing to {href}.",
                     "If the submenu grouping is intentional, ensure the parent nav label "
                     "clearly signals that this offering lives underneath it.",
                     "Verify the change with a fresh crawl to confirm top-level reachability."],
                    "medium",
                ))
        if unmatched:
            examples = [f"'{t}' -> {h}" for t, h in unmatched[:5]]
            findings.append(make_finding(
                "issue", "Homepage-highlighted offerings missing from navigation", "critical",
                f"{site_url}: the following linked, homepage-featured offerings have no "
                f"matching top-level or submenu nav link: {examples}.",
                "Add nav entries (top-level or submenu) for every homepage-highlighted offering.",
                ["Cross-reference homepage offering links against the nav menu's link targets.",
                 "Add a nav or submenu link pointing to each unmatched offering's URL.",
                 "Re-crawl to confirm every offering now has at least one nav path."],
                "critical",
            ))

        vague_found = [t for t, _ in nav_links if t.strip().lower() in
                       {"home", "menu", "more", "other", "misc", "info", "page"}]
        if vague_found:
            findings.append(make_finding(
                "warning", "Vague top-level navigation labels", "medium",
                f"{site_url}: nav contains label(s) {vague_found} that don't indicate content.",
                "Rename vague nav labels to describe what the visitor will find.",
                ["Replace generic labels (e.g. 'More') with the actual category name.",
                 "If the label must stay short, add a descriptive title/aria-label attribute.",
                 "Confirm the new label matches the page's own <h1> and content focus."],
                "medium",
            ))

    dead_nav = []
    checked = 0
    for text, href in nav_links:
        if checked >= 3 or not same_domain(href, site_url):
            continue
        if not can_fetch(rp, href):
            continue
        r2, _, err2 = fetch(href)
        checked += 1
        if r2 is None or r2.status_code >= 400:
            dead_nav.append((text, href, status_desc(r2, err2)))
        elif len(BeautifulSoup(r2.text, "html.parser").get_text(strip=True)) < 150:
            dead_nav.append((text, href, "content too thin (<150 chars visible text)"))
    for text, href, reason in dead_nav:
        findings.append(make_finding(
            "issue", f"Nav item '{text}' leads to a broken or empty page", "high",
            f"{site_url} nav link '{text}' -> {href}: {reason}.",
            f"Fix or remove the '{text}' nav link so it leads to a real, substantive page.",
            [f"If {href} should exist, restore its content or fix the routing/redirect.",
             f"If {href} is deprecated, remove the nav entry or point it to a live replacement.",
             "Re-test the link after the fix to confirm a real page loads."],
            "high",
        ))

    if not any(f["title"].startswith(("No primary", "Homepage-highlighted", "Nav item"))
               for f in findings):
        findings.append(make_finding(
            "opportunity", "Consider grouping related offerings under shared nav categories",
            "low",
            f"{site_url}: nav and homepage offerings are consistent; no defect found.",
            "Evaluate whether related offerings could be grouped into a category to aid scanning.",
            ["Review current nav item count and grouping logic.",
             "If more than ~7 top-level items exist, consider consolidating related ones.",
             "A/B test any regrouping before rolling out broadly."],
            "low",
        ))

    return soup


def check2_orientation(entry_pages, home_soup, site_url, findings, unverified):
    auto_selected = False
    if not entry_pages:
        entry_pages = select_answer_pages(home_soup, site_url)
        auto_selected = True
    if not entry_pages:
        unverified.append({
            "check": "check2_orientation",
            "reason": "no entry_pages provided and no candidate 'answer' pages could be "
                      "auto-selected from the homepage",
        })
        return

    for url in entry_pages:
        if "/fragments/" in url:
            continue
        resp, elapsed, err = fetch(url)
        if resp is None or resp.status_code != 200:
            findings.append(make_finding(
                "issue", f"Entry page unreachable: {url}", "high",
                f"GET {url} failed: {status_desc(resp, err)}"
                + (" (auto-selected as a likely answer page)" if auto_selected else ""),
                "Fix the broken entry page since assistant-referred visitors may land here directly.",
                ["Confirm the URL is correct and not a stale/removed path.",
                 "Restore the page or 301-redirect to its replacement.",
                 "Re-test direct access to the URL."],
                "high",
            ))
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        has_breadcrumb = bool(soup.select('[class*=breadcrumb], [aria-label*=breadcrumb i], '
                                           'nav[aria-label*=breadcrumb i]'))
        has_parent_link = bool(soup.select('a[rel="up"], a[class*=parent], a[class*=back]'))
        orientation_cues = has_breadcrumb or has_parent_link

        clean_text = strip_boilerplate_text(soup)
        h1 = soup.find("h1")
        self_explanatory = bool(h1 and h1.get_text(strip=True)) and len(clean_text) > 300

        main_area = soup.find("main") or soup
        chrome_links = set(main_area.select("nav a, footer a"))
        next_step_links = [a for a in main_area.find_all("a", href=True) if a not in chrome_links]
        has_cta_or_related = len(next_step_links) > 2

        if not orientation_cues and not self_explanatory:
            sev = "critical"
        elif not orientation_cues:
            sev = "high"
        elif not has_cta_or_related:
            sev = "medium"
        else:
            sev = None

        tag = " (auto-selected as a likely answer page)" if auto_selected else ""
        if sev in ("critical", "high"):
            findings.append(make_finding(
                "issue", f"No orientation cues on deep-linked page: {url}", sev,
                f"{url}{tag}: no breadcrumb/parent-link element found "
                f"(checked [class*=breadcrumb], [aria-label*=breadcrumb], a[rel=up]); "
                f"{'page also lacks a clear <h1> or has <300 chars of non-chrome body text' if sev=='critical' else 'page content is otherwise self-explanatory'}.",
                "Add orientation cues so a visitor landing here without prior context isn't lost.",
                ["Add a breadcrumb trail showing the page's place in the site hierarchy.",
                 "Ensure the page has a clear <h1> and enough standalone text to explain "
                 "what it is without requiring the homepage for context.",
                 "Link back to the parent category/section explicitly."],
                "high" if sev == "high" else "critical",
            ))
        elif sev == "medium":
            findings.append(make_finding(
                "warning", f"No clear next step on deep-linked page: {url}", "medium",
                f"{url}{tag}: orientation cues present, but fewer than 3 non-nav/footer links "
                f"found in the main content area (found {len(next_step_links)}).",
                "Add a CTA or related-content links so visitors have somewhere to go next.",
                ["Add a clear call-to-action relevant to this page's topic.",
                 "Add 2-3 related-content links (similar items, next steps, or category browse).",
                 "Avoid dead-ending the visitor after they've read the page content."],
                "medium",
            ))
        else:
            findings.append(make_finding(
                "opportunity", f"Consider referral-aware content on {url}", "low",
                f"{url}{tag}: orientation, self-explanatory content, and next steps are all present.",
                "Strengthen the page for assistant-referred visitors specifically.",
                ["Add a brief framing sentence that works even without prior site context.",
                 "Surface the most likely follow-up questions a visitor referred here might have.",
                 "Keep this content updated as the page's role in the site evolves."],
                "low",
            ))


def check3_link_crawl(site_url, home_soup, findings, unverified, rp):
    visited = set()
    link_status = {}
    page_link_counts = {}
    discovered_links = set()
    body_links_by_page = {}

    def crawl_page(url):
        url = url.split("#")[0]
        if url in visited or len(visited) >= MAX_CRAWL_PAGES:
            return None
        if not same_domain(url, site_url) or not can_fetch(rp, url):
            return None
        visited.add(url)

        resp, elapsed, err = fetch(url)
        if resp is None:
            link_status[url] = f"error: {err}"
            return None
        link_status[url] = resp.status_code
        if resp.status_code >= 400 or "text/html" not in resp.headers.get("Content-Type", ""):
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        chrome = set(urljoin(url, c["href"]) for c in
                     soup.select("nav a[href], footer a[href], header a[href]"))
        body_links_all = [urljoin(url, a["href"]).split("#")[0] for a in
                          soup.find_all("a", href=True)]
        discovered_links.update(body_links_all)
        body_links_by_page[url] = body_links_all

        outlinks_beyond_chrome = [l for l in body_links_all if l not in chrome]
        clean_text_len = len(strip_boilerplate_text(soup))
        page_link_counts[url] = (len(outlinks_beyond_chrome) > 0, clean_text_len > 250)
        return soup, body_links_all

    home_result = crawl_page(site_url)

    nav_targets = []
    if home_soup is not None:
        for _, href in get_nav_links(home_soup, site_url):
            clean = href.split("#")[0]
            if same_domain(clean, site_url) and clean not in nav_targets:
                nav_targets.append(clean)

    level1_children = []
    for nav_url in nav_targets:
        if len(visited) >= MAX_CRAWL_PAGES:
            break
        result = crawl_page(nav_url)
        if result:
            _, body_links_all = result
            level1_children.extend([l for l in body_links_all if same_domain(l, site_url)])

    for child_url in level1_children:
        if len(visited) >= MAX_CRAWL_PAGES:
            break
        crawl_page(child_url)

    broken = {u: s for u, s in link_status.items()
              if (isinstance(s, int) and s >= 400) or isinstance(s, str)}
    home_links = set(body_links_by_page.get(site_url, []))
    for url, status in list(broken.items())[:10]:
        sev = "critical" if url in home_links else "high"
        findings.append(make_finding(
            "issue", "Broken internal link", sev,
            f"{url} returned {status} during crawl of {site_url}.",
            f"Fix or remove the link to {url}.",
            [f"If {url} should have content, restore the page or fix the URL it points to.",
             "If the target is intentionally retired, 301-redirect it to the closest live "
             "equivalent rather than leaving it 404/erroring.",
             "Update or remove any internal links pointing to it."],
            sev,
        ))

    dead_ends = [u for u, (o, c) in page_link_counts.items() if not o and not c]
    for url in dead_ends[:10]:
        findings.append(make_finding(
            "issue", "Dead-end page with no outlinks or substantive content", "medium",
            f"{url}: page loaded (HTTP 200) but has no outlinks beyond nav/header/footer "
            f"and fewer than 250 characters of visible text after removing nav/header/footer "
            f"boilerplate.",
            "Give the page either real content or a path forward.",
            ["Add substantive, page-specific content if this is meant to be a real destination.",
             "If not, add related/next-step links so visitors aren't stuck.",
             "Consider removing or redirecting the page if it serves no purpose."],
            "medium",
        ))

        dead_ends = [u for u, (o, c) in page_link_counts.items() if not o and not c]

        for url in dead_ends[:10]:
            findings.append(make_finding(
                "issue", "Dead-end page with no outlinks or substantive content", "medium",
                f"{url}: page loaded (HTTP 200) but has no outlinks beyond nav/header/footer "
                f"and fewer than 250 characters of visible text after removing nav/header/footer "
                f"boilerplate.",
                "Give the page either real content or a path forward.",
                ["Add substantive, page-specific content if this is meant to be a real destination.",
                "If not, add related/next-step links so visitors aren't stuck.",
                "Consider removing or redirecting the page if it serves no purpose."],
                "medium",
            ))


def check4_mobile(site_url, home_soup, findings):
    if home_soup is None:
        return
    viewport = home_soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        findings.append(make_finding(
            "issue", "No viewport meta tag", "medium",
            f"{site_url}: no <meta name=\"viewport\"> tag found in <head>.",
            "Add a responsive viewport meta tag.",
            ['Add <meta name="viewport" content="width=device-width, initial-scale=1"> '
             "to the <head>.",
             "Verify it's present in the server-rendered HTML, not only injected by JS.",
             "Re-check rendering on a real mobile viewport after adding it."],
            "medium",
        ))
    else:
        content = viewport.get("content", "")
        if "width=device-width" not in content:
            findings.append(make_finding(
                "warning", "Viewport meta tag present but not device-width", "medium",
                f"{site_url}: viewport meta content is '{content}', missing width=device-width.",
                "Update the viewport tag to use device-width scaling.",
                ['Set content="width=device-width, initial-scale=1".',
                 "Avoid fixed pixel widths in the viewport tag.",
                 "Re-test on a narrow viewport to confirm proper scaling."],
                "medium",
            ))

    fixed_width_hits = []
    for tag in home_soup.find_all(style=True):
        m = re.search(r"width:\s*(\d+)px", tag["style"])
        if m and int(m.group(1)) > MOBILE_VIEWPORT_WIDTH:
            fixed_width_hits.append((tag.name, m.group(1)))
    for st in home_soup.find_all("style"):
        for m in re.finditer(r"width:\s*(\d+)px", st.get_text()):
            if int(m.group(1)) > MOBILE_VIEWPORT_WIDTH:
                fixed_width_hits.append(("<style> block", m.group(1)))

    if fixed_width_hits:
        examples = fixed_width_hits[:5]
        findings.append(make_finding(
            "warning", "Fixed-width elements exceeding mobile viewport", "medium",
            f"{site_url}: found {len(fixed_width_hits)} instance(s) of width > "
            f"{MOBILE_VIEWPORT_WIDTH}px (a common mobile viewport reference width, not a "
            f"universal standard) in inline/embedded styles, e.g. {examples}.",
            "Replace fixed pixel widths with responsive units.",
            ["Convert fixed-width layout elements to percentage, max-width, or CSS Grid/Flexbox.",
             "Add a mobile breakpoint that overrides the fixed width below ~415px.",
             "Note: tap-target sizing itself requires rendering and is out of this skill's scope."],
            "medium",
        ))


def check5_performance(site_url, findings):
    resp, elapsed, err = fetch(site_url)
    if resp is None:
        return
    payload_kb = len(resp.content) / 1024
    soup = BeautifulSoup(resp.text, "html.parser")
    head = soup.find("head") or soup
    blocking = head.find_all("script", src=True)
    blocking = [s for s in blocking if not s.get("async") and not s.get("defer")]
    blocking += head.find_all("link", rel="stylesheet")

    slow = elapsed >= SLOW_RESPONSE_SECONDS
    borderline_slow = elapsed >= ACCEPTABLE_RESPONSE_SECONDS
    heavy = payload_kb > 1500 or len(blocking) > 10

    if slow and heavy:
        sev = "critical"
    elif slow:
        sev = "high"
    elif heavy:
        sev = "medium"
    else:
        sev = None

    if sev:
        findings.append(make_finding(
            "issue" if sev in ("critical", "high") else "warning",
            "Slow or heavy initial page load", sev,
            f"{site_url} returned in {elapsed:.2f}s (reference threshold: "
            f"{SLOW_RESPONSE_SECONDS}s), payload {payload_kb:.0f}KB, "
            f"{len(blocking)} synchronous script/stylesheet tag(s) in <head> before content.",
            "Reduce response time and render-blocking resources on first load.",
            ["Add async/defer to non-critical <script> tags in <head>.",
             "Inline or defer non-critical CSS; keep only essential styles render-blocking.",
             "Compress/resize oversized assets and enable server-side caching or a CDN."],
            sev,
        ))
    elif borderline_slow:
        findings.append(make_finding(
            "opportunity", "Response time is borderline", "low",
            f"{site_url} returned in {elapsed:.2f}s (acceptable, but above "
            f"{ACCEPTABLE_RESPONSE_SECONDS}s reference threshold).",
            "Consider proactive performance work before it becomes user-visible.",
            ["Profile server response time under load, not just a single cold request.",
             "Evaluate CDN/caching headers for static assets.",
             "Re-measure periodically as content grows."],
            "low",
        ))

    large_images = []
    for img in soup.find_all("img", src=True)[:15]:
        img_url = urljoin(site_url, img["src"])
        try:
            head_resp = session.head(img_url, timeout=5, allow_redirects=True)
            size = head_resp.headers.get("Content-Length")
            if size and int(size) > 500_000:
                large_images.append((img_url, int(size)))
        except requests.RequestException:
            continue
    if large_images:
        examples = [(u, f"{s/1024:.0f}KB") for u, s in large_images[:5]]
        findings.append(make_finding(
            "warning", "Unusually large image resources on homepage", "medium",
            f"{site_url}: {len(large_images)} image(s) over 500KB detected via "
            f"Content-Length header, e.g. {examples}.",
            "Compress and appropriately size homepage images.",
            ["Re-export large images at web-appropriate resolution and compression.",
             "Serve modern formats (WebP/AVIF) with fallbacks.",
             "Add width/height attributes and lazy-load below-the-fold images."],
            "medium",
        ))



def check6_search(site_url, home_soup, findings, unverified):
    if home_soup is None:
        return
    search_input = home_soup.select_one(
        'input[type="search"], [role="search"], form[action*=search], input[name*=search i]'
    )
    if not search_input:
        offerings = get_featured_offerings(home_soup, site_url)
        if len(offerings) > 8:
            findings.append(make_finding(
                "opportunity", "No on-site search on a content-heavy site", "medium",
                f"{site_url}: no search input, role=search region, or search form action "
                f"detected; homepage links to {len(offerings)} distinct featured offerings.",
                "Add on-site search to help visitors find specific content quickly.",
                ["Add a search input backed by an internal search index or query endpoint.",
                 "Ensure result pages are crawlable and linked (not JS-only islands).",
                 "Surface search prominently in the nav or header."],
                "medium",
            ))
        return

    form = search_input if search_input.name == "form" else search_input.find_parent("form")
    if form and form.get("method", "get").lower() == "get" and form.get("action"):
        action = urljoin(site_url, form["action"])
        query_param = None
        for inp in form.find_all("input"):
            if inp.get("type") in (None, "text", "search"):
                query_param = inp.get("name")
                break
        if query_param:
            candidates = guess_query_terms(home_soup)
            if not candidates:
                unverified.append({
                    "check": "check6_search_quality",
                    "reason": "search endpoint found, but no plausible query term could be "
                              "safely derived from site content",
                })
            else:
                query_term = candidates[0]
                test_url = f"{action}?{query_param}={quote(query_term)}"
                resp, _, err = fetch(test_url)
                if resp is None or resp.status_code >= 400:
                    findings.append(make_finding(
                        "issue", "Site search endpoint errors on a plausible query", "high",
                        f"GET {test_url} (query term '{query_term}', drawn from the site's own "
                        f"nav/heading text) returned {status_desc(resp, err)}.",
                        "Fix the search endpoint so it returns results instead of erroring.",
                        ["Reproduce the error with the same query and inspect server logs.",
                         "Ensure the GET query-param handling matches the rendered form's contract.",
                         "Re-test with several plausible queries after the fix."],
                        "high",
                    ))
                else:
                    result_soup = BeautifulSoup(resp.text, "html.parser")
                    result_text = result_soup.get_text(strip=True).lower()
                    no_results_markers = ["no results", "0 results", "nothing found", "no matches"]
                    looks_empty = any(m in result_text for m in no_results_markers)
                    if looks_empty:
                        findings.append(make_finding(
                            "warning", "Site search returns no results for a plausible query",
                            "high",
                            f"GET {test_url} rendered a 'no results' style message for the "
                            f"query '{query_term}', which was drawn from the site's own nav/heading "
                            f"text (not an arbitrary placeholder).",
                            "Verify the search index actually covers site content for common terms.",
                            ["Re-test with a few more terms known to exist verbatim on the site.",
                             "Check whether the search index is stale or improperly scoped.",
                             "Rebuild/refresh the index if it's out of date."],
                            "high",
                        ))
        else:
            unverified.append({"check": "check6_search_quality",
                                "reason": "search form found but no identifiable text query "
                                          "parameter to safely test"})
    else:
        unverified.append({"check": "check6_search_quality",
                            "reason": "search UI detected but no safe read-only GET endpoint "
                                      "could be identified without submitting a form"})
        findings.append(make_finding(
            "opportunity", "On-site search present (quality unverified)", "low",
            f"{site_url}: a search UI was detected, but its endpoint could not be safely "
            f"queried read-only to assess result quality.",
            "Manually verify search result relevance for a few representative queries.",
            ["Manually test a handful of realistic queries against the search.",
             "Confirm results are relevant and the index is current.",
             "Consider exposing a GET-based query interface for future automated checks."],
            "low",
        ))


def run_audit(site_url, entry_pages=None):
    findings = []
    unverified = []

    rp, robots_issue = load_robots(site_url)
    if robots_issue:
        unverified.append({"check": "robots", "reason": robots_issue})

    home_soup = check1_findability(site_url, findings, unverified, rp)
    check2_orientation(entry_pages or [], home_soup, site_url, findings, unverified)
    check3_link_crawl(site_url, home_soup, findings, unverified, rp)
    check4_mobile(site_url, home_soup, findings)
    check5_performance(site_url, findings)
    check6_search(site_url, home_soup, findings, unverified)

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        if f["severity"] in counts:
            counts[f["severity"]] += 1

    report = {
        "site": site_url,
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total_findings": len(findings),
            **counts,
        },
        "findings": findings,
        "unverified_checks": unverified,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Run the engagement audit against a site.")
    parser.add_argument("site_url", help="Homepage URL of the site to audit")
    parser.add_argument("--entry-pages", nargs="*", default=[],
                         help="One or more deep-page URLs to test for orientation (Check 2). "
                              "If omitted, 1-2 are auto-selected from homepage offerings.")
    args = parser.parse_args()

    report = run_audit(args.site_url, args.entry_pages)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()