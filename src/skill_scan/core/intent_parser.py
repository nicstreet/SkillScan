"""Intent Parser — the first, riskiest piece of the "process chain from prompt
onwards" (see .claude/architecture/project-setup-flow.md). Turns a rough,
informal project idea into a structured build plan, then matches each stage's
needed capabilities against the locally-installed skill corpus.

Two LLM calls, not one, and not N (one per stage) - deliberately, to serve the
token-efficiency goal from the validation protocol (todo.md, "Project Setup &
Skill Supply Chain" -> Validation protocol):
  1. Plan inference - cheap, no skill corpus needed yet.
  2. Local matching - one call covering every stage's needs against the full
     corpus at once, reusing the exact name+description matching mechanism
     already validated empirically by evals/skill_selection/ (the skill-
     selection benchmark), rather than re-deriving a new matching approach.

Deliberately NOT included here: gap detection against external sources, or
anything involving the network. That's the separable, bigger Skill Supply
Chain piece - this module only answers "what's the plan, and what do we
already have locally that helps."
"""

from dataclasses import dataclass, field

from .llm import call_llm_sync, extract_json_object
from .skill_crowding import is_thin_description

_PLAN_SYSTEM = (
    "You turn a rough, informal project idea into a structured build plan. "
    "The user's input may be vague, underspecified, or informal - infer "
    "sensible defaults rather than asking clarifying questions.\n\n"
    "Respond with ONLY a JSON object, no other text, matching this exact shape:\n"
    "{\n"
    "  \"project_type\": \"short label, e.g. 'PyQt6 desktop app', 'Python CLI tool', 'Web API'\",\n"
    '  "stack": "concise stack description, e.g. \'Python 3.13, PyQt6, SQLAlchemy\'",\n'
    '  "summary": "one paragraph restating what will be built, for the user to confirm before anything is built",\n'
    '  "stages": [\n'
    "    {\n"
    '      "name": "stage name, e.g. Setup / Core Build / Testing / Polish",\n'
    '      "goal": "one sentence - what this stage accomplishes",\n'
    '      "skills_needed": ["short capability description", "..."]\n'
    "    }\n"
    "  ]\n"
    "}\n\n"
    "Use 3-5 stages. Keep skills_needed as generic capability descriptions "
    '(e.g. "PDF generation", "PyQt6 frameless window patterns", "writing '
    'pytest tests"), not skill file names - you do not yet know what is '
    "installed locally."
)

_MATCH_SYSTEM = (
    "You match generic capability needs against a library of already-"
    "installed skills, each with a name and description. Only match a skill "
    "if its description genuinely covers the capability - do not force a "
    "match if nothing fits; an empty list is a correct answer.\n\n"
    "Respond with ONLY a JSON object mapping each capability (exact text as "
    "given) to a list of matching skill names (exact names as given):\n"
    '{"capability text": ["skill-name", "..."], "...": []}'
)


@dataclass
class ProcessStage:
    name: str
    goal: str
    skills_needed: list[str] = field(default_factory=list)


@dataclass
class IntentResult:
    project_type: str
    stack: str
    summary: str
    stages: list[ProcessStage] = field(default_factory=list)

    def all_skills_needed(self) -> list[str]:
        """Flattened, de-duplicated capability needs across every stage."""
        seen: list[str] = []
        for stage in self.stages:
            for need in stage.skills_needed:
                if need not in seen:
                    seen.append(need)
        return seen


class IntentParserError(RuntimeError):
    """Raised when the LLM response can't be parsed into the expected shape."""


def parse_intent(rough_idea: str) -> IntentResult:
    """Call 1: infer project type, stack, and a staged plan from a rough idea."""
    response = call_llm_sync(rough_idea, system=_PLAN_SYSTEM, temperature=0.4)
    data = extract_json_object(response)
    if data is None:
        raise IntentParserError(f"Could not parse a JSON plan from: {response[:200]}")

    stages = [
        ProcessStage(
            name=str(s.get("name", "")),
            goal=str(s.get("goal", "")),
            skills_needed=[str(n) for n in s.get("skills_needed", [])],
        )
        for s in data.get("stages", [])
    ]
    return IntentResult(
        project_type=str(data.get("project_type", "")),
        stack=str(data.get("stack", "")),
        summary=str(data.get("summary", "")),
        stages=stages,
    )


def match_local_skills(
    intent: IntentResult, local_skills: dict[str, str]
) -> dict[str, list[str]]:
    """Call 2: match every stage's capability needs against the local corpus
    in one combined call. local_skills: {name: description}.

    Returns {capability_text: [matched_skill_name, ...]} - empty list means
    no local skill covers that need (a real, expected, non-error outcome).
    """
    needs = intent.all_skills_needed()
    if not needs or not local_skills:
        return {need: [] for need in needs}

    # Exclude thin/generic-description skills (e.g. a skill-authoring
    # template) from the candidate pool entirely - found necessary during
    # testing, where such a skill matched against nearly every unrelated
    # capability need. They're never a confident match for anything
    # specific, so they shouldn't be offered as candidates at all.
    specific_skills = {
        name: desc
        for name, desc in local_skills.items()
        if not is_thin_description(desc)
    }
    if not specific_skills:
        return {need: [] for need in needs}

    skill_listing = "\n".join(
        f"- {name}: {desc}" for name, desc in specific_skills.items()
    )
    need_listing = "\n".join(f"- {need}" for need in needs)
    prompt = (
        f"Installed skills:\n{skill_listing}\n\n"
        f"Capabilities needed:\n{need_listing}"
    )
    response = call_llm_sync(prompt, system=_MATCH_SYSTEM, temperature=0.2)
    data = extract_json_object(response)
    if data is None:
        raise IntentParserError(
            f"Could not parse a JSON match result from: {response[:200]}"
        )

    # Validate every returned name against the actual candidate pool rather
    # than trusting the LLM's output - found necessary 2026-06-20 when the
    # local model returned "pyqt6-layout-management" as a match, a plausible
    # -sounding skill name that does not exist in the real 32-skill corpus,
    # despite the prompt explicitly saying "exact names as given". Smaller/
    # local models will do this regardless of instruction wording; the code
    # has to check, not just ask nicely.
    result: dict[str, list[str]] = {}
    for need in needs:
        matches = data.get(need, [])
        if not isinstance(matches, list):
            result[need] = []
            continue
        result[need] = [str(m) for m in matches if str(m) in specific_skills]
    return result
