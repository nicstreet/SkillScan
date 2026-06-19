"""Convert a ScanResult into a Qt-compatible HTML report."""

import html as _html

from ..core.result_store import ScanResult
from ._palette import (
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_STROKE_DIVIDER,
    SYS_TXT_PRIMARY,
    SYS_TXT_MUTED,
    SYS_BORDER_LOW,
    SYS_BADGE_UNSAFE,
    SYS_CRITICAL_LIGHT,
    SYS_BORDER_WARNING,
    SYS_HIGH_LIGHT,
    SYS_BORDER_ADVISORY,
    SYS_MEDIUM_LIGHT,
    SYS_BADGE_SAFE,
    SYS_SAFE_LIGHT,
)

# ── Severity tables ───────────────────────────────────────────────────────────

_SEV_BADGE = {
    "CRITICAL": f"background:{SYS_BADGE_UNSAFE};color:{SYS_CRITICAL_LIGHT};",
    "HIGH": f"background:{SYS_BORDER_WARNING};color:{SYS_HIGH_LIGHT};",
    "MEDIUM": f"background:{SYS_BORDER_ADVISORY};color:{SYS_MEDIUM_LIGHT};",
    # LOW — subdued surface, no alarm colour needed
    "LOW": f"background:{SYS_BG_SECONDARY};color:{SYS_BORDER_LOW};",
    "INFO": f"background:{SYS_BG_SECONDARY};color:{SYS_TXT_MUTED};",
}

_SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

_SAFE_BADGE = f"background:{SYS_BADGE_SAFE};color:{SYS_SAFE_LIGHT};"
_UNSAFE_BADGE = f"background:{SYS_BADGE_UNSAFE};color:{SYS_CRITICAL_LIGHT};"


def _badge(text: str, style: str | None = None) -> str:
    s = style or _SEV_BADGE.get(
        text.upper(), f"background:{SYS_BG_SECONDARY};color:{SYS_TXT_MUTED};"
    )
    return (
        f'<span style="{s} padding:2px 4px; border-radius:4px;'
        f' font-size:12px; font-weight:400;">'
        f"&nbsp;{_html.escape(text)}&nbsp;</span>"
    )


def _slug_to_title(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def format_result_html(result: ScanResult) -> str:
    """Return HTML suitable for QTextBrowser.setHtml()."""
    if not isinstance(result.parsed, dict):
        raw = _html.escape(result.stdout or result.stderr or "No output captured.")
        return (
            f'<html><body style="background:{SYS_BG_PRIMARY};color:{SYS_TXT_MUTED};'
            f'font-family:Segoe UI,sans-serif;font-size:11px;margin:12px;">'
            f"<pre>{raw}</pre></body></html>"
        )

    p = result.parsed
    findings = p.get("findings", [])
    real_finds = [f for f in findings if f.get("rule_id") != "LLM_ANALYSIS_FAILED"]
    real_finds.sort(key=lambda f: _SEV_ORDER.get(f.get("severity", "").upper(), 5))

    parts = []

    # ── Findings table ────────────────────────────────────────────────────
    if real_finds:
        th = (
            f'style="background:{SYS_TXT_MUTED};color:{SYS_TXT_PRIMARY};'
            f"font-size:12px;font-weight:400;"
            f'padding:4px 8px;text-align:left;border-right:1px solid {SYS_STROKE_DIVIDER};"'
        )
        # Uniform style for all non-severity cells
        _cell = f"color:{SYS_TXT_PRIMARY};font-size:12px;font-weight:400;"
        parts.append(
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;">'
            f"<tr>"
            f"<th {th}>Severity</th>"
            f"<th {th}>Category</th>"
            f"<th {th}>Title</th>"
            f"<th {th}>Description</th>"
            f"<th {th}>Remediation</th>"
            f"<th {th}>Analyzer</th>"
            f"</tr>"
        )
        for i, f in enumerate(real_finds):
            sev = f.get("severity", "INFO").upper()
            row_bg = SYS_BG_SECONDARY if i % 2 == 0 else SYS_BG_PRIMARY
            base = (
                f"padding:7px 8px;border-bottom:1px solid {SYS_BG_SECONDARY};"
                f"vertical-align:top;background:{row_bg};"
            )
            parts.append(
                f"<tr>"
                f'<td style="{base}{_cell}">{_html.escape(sev.title())}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("category",""))}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("title",""))}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("description",""))}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("remediation",""))}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("analyzer",""))}</td>'
                f"</tr>"
            )
        parts.append("</table>")
    else:
        parts.append(
            f'<p style="color:{SYS_BADGE_SAFE};text-align:center;margin-top:20px;">'
            f"&#10003;&nbsp; No findings &mdash; this skill appears safe.</p>"
        )

    body = "".join(parts)
    return (
        f'<html><body style="background:{SYS_BG_SECONDARY};color:{SYS_TXT_PRIMARY};'
        f'font-family:Segoe UI,sans-serif;font-size:10px;margin:12px;">'
        f"{body}</body></html>"
    )
