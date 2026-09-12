---
name: audit-orchestrator
description: Coordinates a complete website audit by delegating crawlability, AI discoverability, and on-site engagement checks to the appropriate specialist skills and combining their findings into one prioritized report.
---

# Website Audit Orchestrator

## Purpose

Act as the single entrypoint for the website audit marketplace.

Given a website URL, coordinate the available specialist audit skills and produce one unified, evidence-based report.

This skill is read-only. It must not modify the target website.

## When to use

Use this skill whenever the user asks for a website audit, website analysis, AI discoverability audit, or engagement audit.

## Audit workflow

1. Validate the supplied website URL.
2. Run the crawlability audit to determine whether important pages can be reached and understood by automated crawlers.
3. Run the available AI-discoverability specialist skills.
4. Run the on-site engagement audit.
5. Collect findings from all applicable specialist skills.
6. Remove duplicate findings that describe the same underlying problem.
7. Preserve concrete evidence for every reported issue.
8. Assign or preserve the severity of each finding.
9. Prioritize the recommended actions.
10. Return one unified audit report.

## Specialist skills

Delegate work to the appropriate specialist skills:

- `crawlability` — crawling, robots.txt, HTTP responses, redirects, JavaScript rendering, and page-level HTML extraction.
- `freshness` — freshness and update-related signals.
- `non-text` — non-text content analysis.
- `structured-data` — structured-data analysis.
- `engagement-audit` — on-site engagement and user-action analysis.

Only use a specialist when its scope is relevant to the supplied website and audit.

## Evidence requirements

Every finding must be supported by evidence from the audited website.

Do not report an issue based only on assumptions or generic best practices.

Preserve:

- affected URL
- observed evidence
- severity
- recommended action

When specialist skills return conflicting results, prefer findings supported by stronger direct evidence and avoid speculative conclusions.

## Finding normalization

Normalize specialist findings into the following structure:

{
  "type": "...",
  "severity": "high|medium|low",
  "url": "...",
  "title": "...",
  "evidence": [],
  "recommendation": "..."
}

Avoid reporting the same issue multiple times when multiple specialist skills identify the same underlying problem.

## Prioritization

Prioritize findings using:

1. High-severity issues that prevent or significantly restrict crawling, access, or important content discovery.
2. Medium-severity issues that materially reduce AI discoverability or user engagement.
3. Low-severity quality and optimization issues.

Recommendations should be specific, actionable, and directly connected to the evidence.

## Final report

Return a unified report containing:

- audit summary
- pages analyzed
- high-priority findings
- medium-priority findings
- low-priority findings
- prioritized recommended actions

Each finding should identify the affected URL and provide concrete evidence.

If no issue is detected, do not create a finding.

## Guardrails

- Read-only analysis only.
- Never modify the target website.
- Never submit forms or perform authenticated actions.
- Never bypass robots.txt restrictions.
- Do not intentionally overload the target website.
- Do not invent findings when evidence is unavailable.
- Respect the scope and limitations of each specialist skill.