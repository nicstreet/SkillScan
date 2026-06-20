"""One-off generator for the skill-selection benchmark corpus. Run once;
the generated SKILL.md files are committed, this script is not re-run
automatically. Kept for transparency about how the corpus was authored.
"""

from pathlib import Path

CORPUS = {
    "pdf-builder": "Create, merge, split, and fill PDF documents - extract text and tables from existing PDFs and generate new ones from structured content.",
    "docx-writer": "Create and edit Word documents with headings, tables, styles, and tracked changes for review workflows.",
    "pptx-builder": "Build PowerPoint presentations: slide layouts, charts, speaker notes, and theme-consistent formatting.",
    "xlsx-helper": "Create and edit Excel spreadsheets - formulas, pivot tables, conditional formatting, and charts.",
    "mcp-builder": "Scaffold and implement Model Context Protocol (MCP) servers, including tool definitions, schemas, and transport setup.",
    "web-artifacts-builder": "Build interactive single-page web artifacts (HTML, CSS, JS) for demos, prototypes, and visualisations.",
    "algorithmic-art": "Generate generative and algorithmic art using code-driven visual patterns such as noise fields, flow fields, and tiling.",
    "internal-comms": "Draft internal company communications - announcements, memos, policy updates, and team newsletters.",
    "slack-gif-creator": "Create short animated GIFs sized and formatted for sharing in Slack messages and channels.",
    "brand-guidelines": "Apply a company's brand voice, colour palette, typography, and visual identity rules consistently to content.",
    "frontend-design": "Design and review frontend UI layouts, component hierarchies, spacing systems, and responsive behaviour.",
    "skill-creator": "Scaffold a new Claude Agent Skill - SKILL.md frontmatter, folder structure, and spec validation against agentskills.io.",
    "webapp-testing": "Write and run automated tests for web applications, including browser-driven end-to-end test scripts.",
    "pyqt6-frameless-window": "Build a frameless, rounded-corner PyQt6 window sectioned into columns and rows, with correctly-antialiased corners on both the outer window and its inner panels.",
    "pyqt6-menus": "Build hover-triggered PyQt6 menus that open on mouse-enter and close automatically when the cursor leaves both the trigger button and the menu, plus toggle switches embedded as menu rows.",
    # Deliberately vague negative controls - generic enough to plausibly
    # (and wrongly) match almost any task, testing over-triggering.
    "general-helper": "Helper functions for various tasks.",
    "assistant-tools": "Tools to assist with assorted requests.",
}

root = Path(__file__).parent / "corpus"
for name, description in CORPUS.items():
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n"
        f"# {name.replace('-', ' ').title()}\n\nStub body - this corpus entry exists "
        f"for the skill-selection benchmark, which only reads name + description.\n",
        encoding="utf-8",
    )

print(f"Wrote {len(CORPUS)} corpus entries to {root}")
