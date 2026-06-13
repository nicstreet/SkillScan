"""Convert a ScanResult into a Qt-compatible HTML report."""
import html as _html

from ..core.result_store import ScanResult
from ._palette import (
    ANCHOR, DEEP_SURFACE, LIGHT_CANVAS, MUTED_TEXT, SOFT_SURFACE,
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


def _row(label: str, value: str) -> str:
    return (
        f'<tr>'
        f'<td style="color:{MUTED_TEXT};padding:4px 10px 4px 0;white-space:nowrap;">{label}</td>'
        f'<td style="color:{LIGHT_CANVAS};padding:4px 0;">{value}</td>'
        f'</tr>'
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
    skill_name     = _html.escape(_slug_to_title(p.get("skill_name", "Unknown")))
    skill_path     = _html.escape(p.get("skill_path", result.path))
    is_safe        = p.get("is_safe", True)
    max_sev        = p.get("max_severity", "UNKNOWN")
    findings_count = p.get("findings_count", 0)
    duration       = p.get("scan_duration_seconds", 0)
    analyzers_used = p.get("analyzers_used", [])
    findings       = p.get("findings", [])
    failed         = p.get("analyzers_failed", [])

    safe_badge = _badge("SAFE", _SAFE_BADGE) if is_safe else _badge("UNSAFE", _UNSAFE_BADGE)

    llm_fails  = [f for f in findings if f.get("rule_id") == "LLM_ANALYSIS_FAILED"]
    real_finds = [f for f in findings if f.get("rule_id") != "LLM_ANALYSIS_FAILED"]
    real_finds.sort(key=lambda f: _SEV_ORDER.get(f.get("severity", "").upper(), 5))

    parts = []

    # ── Header ────────────────────────────────────────────────────────────
    parts.append(
        f'<p style="font-size:15px;font-weight:700;color:{LIGHT_CANVAS};margin:0 0 8px 0;">'
        f'{skill_name}</p>'
        f'<table cellpadding="0" cellspacing="2">'
    )
    parts.append(_row("Path",
        f'<span style="font-size:11px;color:{MUTED_TEXT};">{skill_path}</span>'))
    parts.append(_row("Safe",     safe_badge))
    parts.append(_row("Severity", _badge(max_sev)))
    parts.append(_row("Findings",
        f'<b style="color:{LIGHT_CANVAS};">{findings_count}</b>'))
    parts.append(_row("Duration",
        f'<span style="color:{MUTED_TEXT};">{duration:.2f}s</span>'))
    parts.append(_row("Analyzers",
        f'<span style="font-size:11px;color:{MUTED_TEXT};">'
        f'{_html.escape(", ".join(analyzers_used))}</span>'))
    parts.append("</table>")
    parts.append(
        f'<hr style="border:0;border-top:1px solid {DEEP_SURFACE};margin:12px 0;"/>'
    )

    # ── LLM / analyser warning banner ─────────────────────────────────────
    if llm_fails or failed:
        reasons = []
        for fa in failed:
            err = fa.get("error", "")
            if "credit balance is too low" in err:
                reasons.append("API credit balance too low — top up at console.anthropic.com")
            elif "invalid" in err.lower() and "key" in err.lower():
                reasons.append("Invalid API key — check Settings → LLM")
            else:
                reasons.append("Provider error — check Settings → LLM")
        reason = "; ".join(reasons) if reasons else "Check Settings → LLM"
        parts.append(
            f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">'
            f'<tr><td style="background:{HIGH_BG};border-left:3px solid {HIGH_ACCENT};'
            f'padding:8px 12px;border-radius:3px;color:{HIGH_LIGHT};font-size:11px;">'
            f'<b>&#9888; LLM analysis skipped</b> &mdash; {_html.escape(reason)}.'
            f' Scan completed using static analysis only.</td></tr></table>'
        )

    # ── Findings table ────────────────────────────────────────────────────
    if real_finds:
        th = (
            f'style="background:{DEEP_SURFACE};color:{MUTED_TEXT};'
            f'font-size:10px;font-weight:600;letter-spacing:0.5px;'
            f'padding:6px 8px;text-align:left;"'
        )
        parts.append(
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border-collapse:collapse;">'
            f'<tr>'
            f'<th {th}>SEVERITY</th>'
            f'<th {th}>CATEGORY</th>'
            f'<th {th}>TITLE</th>'
            f'<th {th}>DESCRIPTION</th>'
            f'<th {th}>REMEDIATION</th>'
            f'<th {th}>ANALYZER</th>'
            f'</tr>'
        )
        for i, f in enumerate(real_finds):
            sev     = f.get("severity", "INFO").upper()
            row_bg  = ANCHOR if i % 2 == 0 else DEEP_SURFACE
            base    = (
                f'padding:6px 8px;border-bottom:1px solid {DEEP_SURFACE};'
                f'vertical-align:top;background:{row_bg};'
            )
            parts.append(
                f'<tr>'
                f'<td style="{base}">{_badge(sev)}</td>'
                f'<td style="{base}color:{MUTED_TEXT};font-size:11px;">'
                f'{_html.escape(f.get("category",""))}</td>'
                f'<td style="{base}color:{LIGHT_CANVAS};font-size:11px;font-weight:600;">'
                f'{_html.escape(f.get("title",""))}</td>'
                f'<td style="{base}color:{MUTED_TEXT};font-size:11px;">'
                f'{_html.escape(f.get("description",""))}</td>'
                f'<td style="{base}color:{SOFT_SURFACE};font-size:11px;font-style:italic;">'
                f'{_html.escape(f.get("remediation",""))}</td>'
                f'<td style="{base}color:{MUTED_TEXT};font-size:10px;">'
                f'{_html.escape(f.get("analyzer",""))}</td>'
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
