from __future__ import annotations

import re
from typing import Iterable

from pydantic import BaseModel, Field

from madd.core.scenario import Scenario
from madd.tools.web_search import (
    DEFAULT_LAW_DOMAINS,
    DEFAULT_SECURITY_DOMAINS,
    DEFAULT_ECON_DOMAINS,
    DEFAULT_ENV_DOMAINS,
    DEFAULT_RIGHTS_DOMAINS,
)

DEFAULT_INSTITUTION_NAME = "Joint Oversight Commission (JOC)"

ARCHETYPE_ORDER = [
    "SECURITY_DEFENSE",
    "TERRITORIAL_BORDER",
    "RESOURCES_MINERALS",
    "TRADE_SANCTIONS_FINANCE",
    "ENVIRONMENT_CLIMATE",
    "HUMAN_RIGHTS_COMMUNITY",
    "CYBER_TECH",
    "WATER_FOOD_ENERGY",
]

ARCHETYPE_KEYWORDS = {
    "SECURITY_DEFENSE": [
        "defense", "military", "basing", "access", "nato", "deterrence",
        "de-escalation", "hotline", "forces", "deployment", "wmd",
    ],
    "TERRITORIAL_BORDER": [
        "sovereignty", "border", "territorial", "claim", "demarcation", "eez",
        "unclos", "arbitration",
    ],
    "RESOURCES_MINERALS": [
        "critical minerals", "rare earth", "mining", "oil", "gas", "extraction",
        "licensing", "offtake", "processing",
    ],
    "TRADE_SANCTIONS_FINANCE": [
        "sanctions", "tariff", "export control", "end-use", "dual-use",
        "investment screening", "fdi",
    ],
    "ENVIRONMENT_CLIMATE": [
        "environment", "eia", "esia", "climate", "biodiversity", "protected",
        "pollution", "monitoring",
    ],
    "HUMAN_RIGHTS_COMMUNITY": [
        "indigenous", "fpic", "community", "human rights", "displacement",
        "minority", "grievance",
    ],
    "CYBER_TECH": [
        "cyber", "data", "ai", "technology transfer", "surveillance",
        "semiconductor",
    ],
    "WATER_FOOD_ENERGY": [
        "water", "river", "dam", "food security", "energy grid",
    ],
}

BASE_RESEARCH_TOPICS = {
    "economy": "GDP economy trade industries",
    "leaders": "government president prime minister leaders",
    "alliances": "foreign policy alliances treaties international relations",
    "history": "major conflicts history wars",
}

ARCHETYPE_RESEARCH_TOPICS = {
    "SECURITY_DEFENSE": {
        "defense_posture": "defense posture basing access force posture",
        "confidence_building": "confidence building measures hotline deconfliction",
        "incident_history": "incident history crises escalation de-escalation",
        "defense_agreements": "defense agreements status of forces",
    },
    "TERRITORIAL_BORDER": {
        "border_law": "border law demarcation arbitration claims",
        "treaty_law": "treaty framework dispute settlement",
    },
    "RESOURCES_MINERALS": {
        "mining_law": "mining law licensing royalties regulatory framework",
        "critical_minerals": "critical minerals rare earths processing",
        "supply_chain": "supply chain offtake processing local value",
        "esg": "anti-corruption transparency audit ESG",
    },
    "TRADE_SANCTIONS_FINANCE": {
        "trade_policy": "trade policy tariffs customs",
        "sanctions": "sanctions export controls licensing",
        "investment_screening": "investment screening FDI review",
    },
    "ENVIRONMENT_CLIMATE": {
        "environment": "environment climate biodiversity EIA ESIA",
        "monitoring": "environmental monitoring reporting standards",
    },
    "HUMAN_RIGHTS_COMMUNITY": {
        "human_rights": "human rights indigenous FPIC community consultation",
        "grievance": "grievance mechanisms ombudsperson community benefits",
    },
    "CYBER_TECH": {
        "cyber_policy": "cyber policy incident response",
        "technology_transfer": "technology transfer dual-use controls",
    },
    "WATER_FOOD_ENERGY": {
        "water_sharing": "water sharing river basin agreements",
        "energy_grid": "energy grid interconnection reliability",
        "food_security": "food security supply stability",
    },
}

TOPIC_DOMAIN_MAP = {
    "economy": DEFAULT_ECON_DOMAINS,
    "leaders": DEFAULT_SECURITY_DOMAINS,
    "alliances": DEFAULT_SECURITY_DOMAINS,
    "history": DEFAULT_SECURITY_DOMAINS,
    "law": DEFAULT_LAW_DOMAINS,
    "environment": DEFAULT_ENV_DOMAINS,
    "human_rights": DEFAULT_RIGHTS_DOMAINS,
    "defense_posture": DEFAULT_SECURITY_DOMAINS,
    "confidence_building": DEFAULT_SECURITY_DOMAINS,
    "incident_history": DEFAULT_SECURITY_DOMAINS,
    "defense_agreements": DEFAULT_SECURITY_DOMAINS,
    "border_law": DEFAULT_LAW_DOMAINS,
    "treaty_law": DEFAULT_LAW_DOMAINS,
    "mining_law": DEFAULT_ECON_DOMAINS,
    "critical_minerals": DEFAULT_ECON_DOMAINS,
    "supply_chain": DEFAULT_ECON_DOMAINS,
    "esg": DEFAULT_ECON_DOMAINS,
    "trade_policy": DEFAULT_ECON_DOMAINS,
    "sanctions": DEFAULT_ECON_DOMAINS,
    "investment_screening": DEFAULT_ECON_DOMAINS,
    "monitoring": DEFAULT_ENV_DOMAINS,
    "grievance": DEFAULT_RIGHTS_DOMAINS,
    "cyber_policy": DEFAULT_SECURITY_DOMAINS,
    "technology_transfer": DEFAULT_ECON_DOMAINS,
    "water_sharing": DEFAULT_LAW_DOMAINS,
    "energy_grid": DEFAULT_ECON_DOMAINS,
    "food_security": DEFAULT_ECON_DOMAINS,
}

ARCHETYPE_VERIFIER_KEYWORDS = {
    "SECURITY_DEFENSE": [
        "basing", "status of forces", "deployment", "hotline", "inspection",
        "nuclear", "wmd", "deterrence",
    ],
    "TERRITORIAL_BORDER": [
        "sovereignty", "demarcation", "eez", "unclos", "arbitration",
    ],
    "RESOURCES_MINERALS": [
        "critical minerals", "rare earth", "license", "offtake", "processing",
        "royalty", "beneficial ownership",
    ],
    "TRADE_SANCTIONS_FINANCE": [
        "sanctions", "tariff", "export control", "end-use", "investment screening",
    ],
    "ENVIRONMENT_CLIMATE": [
        "esia", "eia", "biodiversity", "pollution", "remediation", "protected",
    ],
    "HUMAN_RIGHTS_COMMUNITY": [
        "indigenous", "fpic", "human rights", "grievance", "resettlement",
    ],
    "CYBER_TECH": [
        "cyber", "data", "ai", "surveillance", "semiconductor",
    ],
    "WATER_FOOD_ENERGY": [
        "river", "dam", "water sharing", "energy grid", "food security",
    ],
}

ARCHETYPE_ANNEX_TEMPLATES = {
    "SECURITY_DEFENSE": [
        "Annex on notification, deconfliction, and hotlines",
        "Annex on visiting forces principles",
    ],
    "TERRITORIAL_BORDER": [
        "Annex on maps, coordinates, and technical commission procedures",
    ],
    "RESOURCES_MINERALS": [
        "Annex on licensing, revenue sharing, and supply-chain traceability",
    ],
    "ENVIRONMENT_CLIMATE": [
        "Annex on ESIA standards and monitoring protocol",
    ],
    "HUMAN_RIGHTS_COMMUNITY": [
        "Annex on FPIC thresholds and grievance procedures",
    ],
    "TRADE_SANCTIONS_FINANCE": [
        "Annex on export controls, licensing, and compliance reporting",
    ],
    "CYBER_TECH": [
        "Annex on cyber incident reporting and technology safeguards",
    ],
    "WATER_FOOD_ENERGY": [
        "Annex on water sharing and infrastructure coordination",
    ],
}

ARCHETYPE_DEFINITIONS = {
    "SECURITY_DEFENSE": [
        "Temporary access",
        "Permanent basing",
        "Deconfliction",
    ],
    "TERRITORIAL_BORDER": [
        "Disputed area",
        "Demarcation",
    ],
    "RESOURCES_MINERALS": [
        "Critical minerals",
        "Offtake",
        "Local value creation",
    ],
    "ENVIRONMENT_CLIMATE": [
        "ESIA/EIA",
        "Protected area",
        "Remediation bond",
    ],
    "HUMAN_RIGHTS_COMMUNITY": [
        "FPIC",
        "Community benefit agreement",
        "Grievance mechanism",
    ],
    "TRADE_SANCTIONS_FINANCE": [
        "Export control",
        "End-use verification",
    ],
    "CYBER_TECH": [
        "Dual-use technology",
        "Incident response",
    ],
    "WATER_FOOD_ENERGY": [
        "Water allocation",
        "Critical infrastructure",
    ],
}

ARCHETYPE_PROMPT_REQUIREMENTS = {
    "SECURITY_DEFENSE": [
        'Define "temporary access" vs "permanent basing".',
        "Include notification timeline, deconfliction/hotline, and oversight/inspection.",
        "Avoid operational overpromises; focus on approvals and mechanisms.",
    ],
    "TERRITORIAL_BORDER": [
        "Avoid definitive sovereignty rulings; frame as proposals and processes.",
        "Include mapping/technical commission option and dispute ladder.",
    ],
    "RESOURCES_MINERALS": [
        "Specify licensing criteria, screening, transparency, and audit rights.",
        "Cover offtake/processing, local value creation, and revenue/benefit sharing.",
    ],
    "ENVIRONMENT_CLIMATE": [
        "Specify ESIA/EIA standards, monitoring protocol, and no-go zones.",
        "Require remediation bonds and independent verification.",
    ],
    "HUMAN_RIGHTS_COMMUNITY": [
        "Clarify FPIC vs consultation thresholds.",
        "Include grievance mechanism and community benefit agreements.",
    ],
    "TRADE_SANCTIONS_FINANCE": [
        "Specify export control licensing, end-use checks, and compliance audits.",
        "Include appeal procedures and transparency safeguards.",
    ],
    "CYBER_TECH": [
        "Specify incident reporting, audits, and technology safeguards.",
    ],
    "WATER_FOOD_ENERGY": [
        "Specify allocation rules, data sharing, and infrastructure safeguards.",
    ],
}

ARCHETYPE_NONTRIVIAL_CLAIMS = {
    "SECURITY_DEFENSE": [
        "force levels, basing rights, defense treaties, incident history",
    ],
    "TERRITORIAL_BORDER": [
        "legal status, boundaries, arbitral rulings, maps/coordinates",
    ],
    "RESOURCES_MINERALS": [
        "reserves, production volumes, licensing law, ownership structures",
    ],
    "TRADE_SANCTIONS_FINANCE": [
        "sanctions regimes, tariff schedules, export control lists",
    ],
    "ENVIRONMENT_CLIMATE": [
        "impact standards, protected area designations, emissions data",
    ],
    "HUMAN_RIGHTS_COMMUNITY": [
        "rights status, displacement figures, consultation outcomes",
    ],
    "CYBER_TECH": [
        "incident statistics, attribution claims, technical capabilities",
    ],
    "WATER_FOOD_ENERGY": [
        "allocation volumes, reservoir capacity, grid interconnection data",
    ],
}


class ArchetypeScore(BaseModel):
    archetype: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)


class RouterPlan(BaseModel):
    archetypes: list[ArchetypeScore] = Field(default_factory=list)
    institution_name: str = DEFAULT_INSTITUTION_NAME
    legal_hooks: list[str] = Field(default_factory=list)
    research_topics: dict[str, str] = Field(default_factory=dict)
    topic_domains: dict[str, list[str]] = Field(default_factory=dict)
    turn_prompt_patch: str = ""
    verifier_keywords: list[str] = Field(default_factory=list)
    treaty_annex_templates: list[str] = Field(default_factory=list)
    treaty_definitions: list[str] = Field(default_factory=list)


def build_router_plan(scenario: Scenario) -> RouterPlan:
    text = _scenario_text(scenario).lower()
    agenda_texts = _agenda_texts(scenario)
    scores = []
    for archetype in ARCHETYPE_ORDER:
        score = _score_archetype(archetype, text, agenda_texts)
        scores.append(ArchetypeScore(archetype=archetype, score=score))

    active = [s.archetype for s in scores if s.score >= 0.4]
    research_topics = dict(BASE_RESEARCH_TOPICS)
    for archetype in ARCHETYPE_ORDER:
        if archetype in active:
            research_topics.update(ARCHETYPE_RESEARCH_TOPICS.get(archetype, {}))

    topic_domains = {}
    for topic_key in research_topics:
        domains = TOPIC_DOMAIN_MAP.get(topic_key)
        if not domains:
            domains = _domains_for_topic(topic_key)
        topic_domains[topic_key] = list(domains) if domains else []

    institution_name = _detect_institution_name(_scenario_text(scenario))
    legal_hooks = _extract_legal_hooks(_scenario_text(scenario))
    verifier_keywords = _build_verifier_keywords(active)
    treaty_annex_templates = _build_annex_templates(active)
    treaty_definitions = _build_definitions(active)
    turn_prompt_patch = _build_turn_prompt_patch(active, scores, legal_hooks)

    return RouterPlan(
        archetypes=scores,
        institution_name=institution_name,
        legal_hooks=legal_hooks,
        research_topics=research_topics,
        topic_domains=topic_domains,
        turn_prompt_patch=turn_prompt_patch,
        verifier_keywords=verifier_keywords,
        treaty_annex_templates=treaty_annex_templates,
        treaty_definitions=treaty_definitions,
    )


def _score_archetype(archetype: str, base_text: str, agenda_texts: list[tuple[str, float]]) -> float:
    keywords = ARCHETYPE_KEYWORDS.get(archetype, [])
    score = 0.0
    for keyword in keywords:
        if keyword in base_text:
            score += 1.0
    for agenda_text, multiplier in agenda_texts:
        for keyword in keywords:
            if keyword in agenda_text:
                score += 1.0 * multiplier
    threshold = 3.0
    return min(1.0, score / threshold)


def _scenario_text(scenario: Scenario) -> str:
    agenda_lines = []
    for item in scenario.agenda:
        agenda_lines.append(item.topic)
        if item.description:
            agenda_lines.append(item.description)
    return "\n".join([scenario.name, scenario.description, "\n".join(agenda_lines)])


def _agenda_texts(scenario: Scenario) -> list[tuple[str, float]]:
    agenda_texts = []
    for item in scenario.agenda:
        text = f"{item.topic} {item.description or ''}".lower()
        if item.priority == 1:
            multiplier = 2.0
        elif item.priority == 2:
            multiplier = 1.5
        else:
            multiplier = 1.0
        agenda_texts.append((text, multiplier))
    return agenda_texts


def _detect_institution_name(text: str) -> str:
    match = re.search(r"\b[A-Z]{3,8}\b", text)
    if match:
        return match.group(0)
    return DEFAULT_INSTITUTION_NAME


def _extract_legal_hooks(text: str) -> list[str]:
    hooks: list[str] = []
    pattern = re.compile(r"\b\d{4}\b[^.\n]{0,80}\b(treaty|agreement|framework)\b", re.IGNORECASE)
    for match in pattern.finditer(text):
        hook = match.group(0).strip()
        if hook and hook not in hooks:
            hooks.append(hook)

    explicit_terms = [
        "UNCLOS",
        "UN Charter",
        "Geneva Conventions",
        "Vienna Convention",
        "NPT",
        "WTO",
    ]
    for term in explicit_terms:
        if term.lower() in text.lower() and term not in hooks:
            hooks.append(term)
    return hooks


def _build_verifier_keywords(active: Iterable[str]) -> list[str]:
    keywords = []
    for archetype in active:
        keywords.extend(ARCHETYPE_VERIFIER_KEYWORDS.get(archetype, []))
    return sorted({k.lower() for k in keywords})


def _build_annex_templates(active: Iterable[str]) -> list[str]:
    templates = [
        "Annex on verification, monitoring, and reporting",
        "Annex on implementation timelines",
        "Annex on dispute resolution steps",
    ]
    for archetype in active:
        templates.extend(ARCHETYPE_ANNEX_TEMPLATES.get(archetype, []))
    return _dedupe_list(templates)


def _build_definitions(active: Iterable[str]) -> list[str]:
    definitions = []
    for archetype in active:
        definitions.extend(ARCHETYPE_DEFINITIONS.get(archetype, []))
    return _dedupe_list(definitions)


def _build_turn_prompt_patch(active: list[str], scores: list[ArchetypeScore], legal_hooks: list[str]) -> str:
    score_text = ", ".join(f"{s.archetype}({s.score:.2f})" for s in scores if s.score > 0)
    lines = [
        f"Router: This scenario is primarily {', '.join(active) or 'GENERAL'}; scores: {score_text or 'none'}.",
        "Agenda emphasis: address agenda items in priority order and be mechanism-specific.",
    ]
    for archetype in active:
        reqs = ARCHETYPE_PROMPT_REQUIREMENTS.get(archetype, [])
        if reqs:
            lines.append(f"{archetype} requirements: " + " ".join(reqs))

    claim_lines = []
    for archetype in active:
        claim_lines.extend(ARCHETYPE_NONTRIVIAL_CLAIMS.get(archetype, []))
    if claim_lines:
        lines.append(
            "Non-trivial factual claims include: "
            + "; ".join(_dedupe_list(claim_lines))
            + "."
        )

    lines.append(
        "Clause checklist: scope, authority, timelines, compliance/enforcement, "
        "exceptions, reporting cadence."
    )

    if legal_hooks:
        lines.append("Legal hooks mentioned in scenario (do not assert beyond text): " + "; ".join(legal_hooks))

    return "\n".join(lines)


def _domains_for_topic(topic_key: str) -> list[str]:
    key = topic_key.lower()
    if any(token in key for token in ("law", "treaty", "arbitration", "border", "sovereign")):
        return DEFAULT_LAW_DOMAINS
    if any(token in key for token in ("defense", "security", "basing", "alliance", "incident", "military", "cyber")):
        return DEFAULT_SECURITY_DOMAINS
    if any(token in key for token in ("economy", "trade", "investment", "sanction", "export", "finance", "mineral", "mining", "supply")):
        return DEFAULT_ECON_DOMAINS
    if any(token in key for token in ("environment", "climate", "biodiversity", "esia", "eia", "pollution", "monitor")):
        return DEFAULT_ENV_DOMAINS
    if any(token in key for token in ("rights", "human", "indigenous", "fpic", "community", "grievance", "labor")):
        return DEFAULT_RIGHTS_DOMAINS
    return DEFAULT_SECURITY_DOMAINS


def _dedupe_list(items: list[str]) -> list[str]:
    seen = set()
    unique = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique
