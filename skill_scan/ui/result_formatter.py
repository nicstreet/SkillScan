"""Convert a ScanResult into a Qt-compatible HTML report."""
import html as _html

from ..core.result_store import ScanResult
from ._palette import (
    ANCHOR, DEEP_SURFACE, HOVER_FOCUS, LIGHT_CANVAS, MUTED_TEXT, SOFT_SURFACE,
    CRITICAL_ACCENT, CRITICAL_BG, CRITICAL_LIGHT,
    HIGH_ACCENT, HIGH_BG, HIGH_LIGHT,
    MEDIUM_ACCENT, MEDIUM_BG, MEDIUM_LIGHT,
    SAFE_ACCENT, SAFE_BG, SAFE_LIGHT,
)

# ── Severity tables ───────────────────────────────────────────────────────────

_SEV_BADGE = {
    "CRITICAL": f"background:{CRITICAL_ACCENT};color:{CRITICAL_LIGHT};",
    "HIGH":     f"background:{HIGH_ACCENT};color:{HIGH_LIGHT};",
    "MEDIUM":   f"background:{MEDIUM_ACCENT};color:{MEDIUM_LIGHT};",
    # LOW — subdued surface, no alarm colour needed
    "LOW":      f"background:{DEEP_SURFACE};color:{SOFT_SURFACE};",
    "INFO":     f"background:{DEEP_SURFACE};color:{MUTED_TEXT};",
}

_SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

_SAFE_BADGE   = f"background:{SAFE_ACCENT};color:{SAFE_LIGHT};"
_UNSAFE_BADGE = f"background:{CRITICAL_ACCENT};color:{CRITICAL_LIGHT};"


def _badge(text: str, style: str | None = None) -> str:
    s = style or _SEV_BADGE.get(text.upper(), f"background:{DEEP_SURFACE};color:{MUTED_TEXT};")
    return (
        f'<span style="{s} padding:2px 0; border-radius:4px;'
        f' font-size:10px; font-weight:700;">'
        f'&nbsp;{_html.escape(text)}&nbsp;</span>'
    )


def _slug_to_title(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def format_result_html(result: ScanResult) -> str:
    """Return HTML suitable for QTextBrowser.setHtml()."""
    if not isinstance(result.parsed, dict):
        raw = _html.escape(result.stdout or result.stderr or "No output captured.")
        return (
            f'<html><body style="background:{ANCHOR};color:{MUTED_TEXT};'
            f'font-family:Segoe UI,sans-serif;font-size:11px;margin:12px;">'
            f'<pre>{raw}</pre></body></html>'
        )

    p = result.parsed
    findings = p.get("findings", [])
    failed   = p.get("analyzers_failed", [])

    llm_fails  = [f for f in findings if f.get("rule_id") == "LLM_ANALYSIS_FAILED"]
    real_finds = [f for f in findings if f.get("rule_id") != "LLM_ANALYSIS_FAILED"]
    real_finds.sort(key=lambda f: _SEV_ORDER.get(f.get("severity", "").upper(), 5))

    parts = []

    # ── Findings table ────────────────────────────────────────────────────
    if real_finds:
        th = (
            f'style="background:{HOVER_FOCUS};color:{LIGHT_CANVAS};'
            f'font-size:12px;font-weight:600;'
            f'padding:7px 8px;text-align:left;"'
        )
        # Uniform style for all non-severity cells
        _cell = f"color:{LIGHT_CANVAS};font-size:12px;font-weight:400;"
        parts.append(
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;">'
            f'<tr>'
            f'<th {th}>Severity</th>'
            f'<th {th}>Category</th>'
            f'<th {th}>Title</th>'
            f'<th {th}>Description</th>'
            f'<th {th}>Remediation</th>'
            f'<th {th}>Analyzer</th>'
            f'</tr>'
        )
        for i, f in enumerate(real_finds):
            sev    = f.get("severity", "INFO").upper()
            row_bg = ANCHOR if i % 2 == 0 else DEEP_SURFACE
            base   = (
                f'padding:7px 8px;border-bottom:1px solid {DEEP_SURFACE};'
                f'vertical-align:top;background:{row_bg};'
            )
            parts.append(
                f'<tr>'
                f'<td style="{base}">{_badge(sev)}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("category",""))}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("title",""))}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("description",""))}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("remediation",""))}</td>'
                f'<td style="{base}{_cell}">{_html.escape(f.get("analyzer",""))}</td>'
                f'</tr>'
            )
        parts.append("</table>")
    else:
        parts.append(
            f'<p style="color:{SAFE_ACCENT};text-align:center;margin-top:20px;">'
            f'&#10003;&nbsp; No findings &mdash; this skill appears safe.</p>'
        )

    body = "".join(parts)
    return (
        f'<html><body style="background:{ANCHOR};color:{LIGHT_CANVAS};'
        f'font-family:Segoe UI,sans-serif;font-size:12px;margin:12px;">'
        f'{body}</body></html>'
    )
