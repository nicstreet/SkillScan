"""Shared HTML renderer for spec-compliance results.

Used by Skill Detail's Compliance tab and the Skill Audit view's detail
panel — extracted so both render the identical breakdown rather than
maintaining two copies. Presentation (palette tokens, markup) lives here;
core/spec_compliance.py stays pure scoring logic with no UI imports.
"""

import html as _html

from ..core.skill_budget import (
    PER_SKILL_CAP_CURRENT,
    PER_SKILL_CAP_LEGACY,
    check_description_length,
)
from ..core.spec_compliance import RECOMMENDED_FIELDS, REQUIRED_FIELDS, ComplianceResult
from ._palette import (
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BORDER_ADVISORY,
    SYS_BORDER_WARNING,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
)


def score_colour(score: int) -> str:
    """Colour token for a compliance score: green >=75, amber >=50, red below."""
    if score >= 75:
        return SYS_BADGE_SAFE
    if score >= 50:
        return SYS_BORDER_ADVISORY
    return SYS_BADGE_UNSAFE


def render_compliance_html(meta: dict, result: ComplianceResult) -> str:
    """Render a ComplianceResult + parsed frontmatter as a Compliance tab page."""
    score = result.score
    colour = score_colour(score)

    parts = [
        f'<html><body style="background:{SYS_BG_PRIMARY};color:{SYS_TXT_PRIMARY};'
        f'font-family:Segoe UI,sans-serif;font-size:12px;margin:24px;">',
        # Score row
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">',
        "<tr>",
        f'<td style="font-size:13px;font-weight:700;color:{SYS_TXT_PRIMARY};'
        f'padding-bottom:10px;">SPEC COMPLIANCE SCORE</td>',
        f'<td style="text-align:right;font-size:22px;font-weight:700;'
        f'color:{colour};padding-bottom:10px;">{score}</td>',
        "</tr></table>",
        # Score bar
        f'<div style="background:{SYS_BG_SECONDARY};border-radius:4px;height:8px;'
        f'width:100%;margin-bottom:20px;">',
        f'<div style="background:{colour};border-radius:4px;height:8px;'
        f'width:{score}%;"></div></div>',
    ]

    # Required fields
    parts.append(
        f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
        f'letter-spacing:1px;margin-bottom:8px;">REQUIRED FIELDS</p>'
    )
    parts.append(
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;margin-bottom:20px;">'
    )
    for f in REQUIRED_FIELDS:
        present = bool(meta.get(f))
        icon = (
            f'<span style="color:{SYS_BADGE_SAFE};">&#10003;</span>'
            if present
            else f'<span style="color:{SYS_BADGE_UNSAFE};">&#10007;</span>'
        )
        val = (
            _html.escape(str(meta[f])[:60])
            if present
            else f'<span style="color:{SYS_BADGE_UNSAFE};">missing</span>'
        )
        parts.append(
            f'<tr style="border-bottom:1px solid {SYS_BG_SECONDARY};">'
            f'<td style="padding:5px 8px;width:20px;">{icon}</td>'
            f'<td style="padding:5px 8px;color:{SYS_TXT_PRIMARY};font-weight:600;">'
            f"{_html.escape(f)}</td>"
            f'<td style="padding:5px 8px;color:{SYS_TXT_MUTED};">{val}</td>'
            f"</tr>"
        )
    parts.append("</table>")

    # Recommended fields
    parts.append(
        f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
        f'letter-spacing:1px;margin-bottom:8px;">RECOMMENDED FIELDS</p>'
    )
    parts.append(
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;margin-bottom:20px;">'
    )
    for f in RECOMMENDED_FIELDS:
        present = bool(meta.get(f))
        icon = (
            f'<span style="color:{SYS_BADGE_SAFE};">&#10003;</span>'
            if present
            else f'<span style="color:{SYS_BORDER_ADVISORY};">&#9679;</span>'
        )
        val = (
            _html.escape(str(meta[f])[:60])
            if present
            else f'<span style="color:{SYS_BORDER_ADVISORY};">not set</span>'
        )
        parts.append(
            f'<tr style="border-bottom:1px solid {SYS_BG_SECONDARY};">'
            f'<td style="padding:5px 8px;width:20px;">{icon}</td>'
            f'<td style="padding:5px 8px;color:{SYS_TXT_PRIMARY};font-weight:600;">'
            f"{_html.escape(f)}</td>"
            f'<td style="padding:5px 8px;color:{SYS_TXT_MUTED};">{val}</td>'
            f"</tr>"
        )
    parts.append("</table>")

    # Issues — structural problems on present fields + body-budget warnings,
    # neither of which fit the present/missing checklist above.
    issues = result.name_errors + result.description_errors + result.body_warnings
    if issues:
        parts.append(
            f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
            f'letter-spacing:1px;margin-bottom:8px;">ISSUES</p>'
        )
        parts.append('<ul style="margin:0 0 20px;padding-left:18px;">')
        for issue in issues:
            parts.append(
                f'<li style="color:{SYS_BORDER_WARNING};padding:2px 0;">'
                f"{_html.escape(issue)}</li>"
            )
        parts.append("</ul>")

    # Claude Code skill-listing budget — informational only, not part of the
    # formal spec, see core/skill_budget.py. Community-sourced and known to
    # change between Claude Code versions; don't treat as certain.
    budget = check_description_length(str(meta.get("description") or ""))
    if budget.over_legacy_cap:
        budget_colour = (
            SYS_BADGE_UNSAFE if budget.over_current_cap else SYS_BORDER_ADVISORY
        )
        note = (
            f"exceeds the {PER_SKILL_CAP_CURRENT}-char current display cap"
            if budget.over_current_cap
            else f"exceeds the older {PER_SKILL_CAP_LEGACY}-char display cap "
            f"(some Claude Code versions truncate beyond this)"
        )
        parts.append(
            f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
            f'letter-spacing:1px;margin-bottom:8px;">DESCRIPTION LENGTH</p>'
        )
        parts.append(
            f'<p style="color:{budget_colour};margin:0 0 20px;">'
            f"{budget.description_length} characters — {note}. Claude Code's "
            f"available_skills listing has an undocumented, version-dependent "
            f"character budget shared across all installed skills — see "
            f"url.md for sources.</p>"
        )

    parts.append("</body></html>")
    return "".join(parts)
