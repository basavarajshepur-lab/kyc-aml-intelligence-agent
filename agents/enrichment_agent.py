"""
Entity Enrichment Agent — screens an entity across sanctions lists, PEP databases,
adverse media, corporate registries, and geographic risk.

Uses Claude tool use in an agentic loop — the agent decides which tools to call
and in what order based on the entity type and what it finds. An individual
gets a different enrichment path from a company; a name match on sanctions
triggers deeper investigation.

Mock data reflects realistic Worldcheck/ComplyAdvantage patterns:
- Fuzzy name matching with scored confidence
- PEP tiers (head of state → local official)
- FATF greylist/blacklist country risk
- PSC/UBO beneficial ownership depth

In production: replace mock functions with Worldcheck API, ComplyAdvantage,
Companies House API, FATF/Basel AML Index feeds.

Design connection: mirrors the VEDaaS entity verification + Worldcheck screening
pipeline built at LSEG — where entity enrichment fed downstream risk assessment
across 40,000+ financial institutions.
"""

import json
from anthropic import Anthropic
from ..core.models import (
    EnrichedEntity, EntityType, SanctionsHit, PEPRecord,
    AdverseMediaHit, CompanyRegistryData, GeographicRisk
)

client = Anthropic()

# ── Mock data stores ──────────────────────────────────────────────────────────

SANCTIONS_DATABASE = {
    "viktor petrov": [
        SanctionsHit(
            list_name="OFAC_SDN", match_type="EXACT", match_score=0.98,
            entry_type="individual", listed_date="2022-02-25",
            program="RUSSIA",
            entry_details="Senior official of the Russian Ministry of Finance. SDN designation under EO 14024.",
        )
    ],
    "atlas trading international": [
        SanctionsHit(
            list_name="HMT", match_type="EXACT", match_score=0.95,
            entry_type="entity", listed_date="2023-05-12",
            program="GLOBAL_SANCTIONS",
            entry_details="Entity designated for facilitating sanctions evasion on behalf of designated Russian nationals.",
        )
    ],
    "sunrise holdings": [
        SanctionsHit(
            list_name="UN_CONSOLIDATED", match_type="FUZZY", match_score=0.71,
            entry_type="entity", listed_date="2019-08-01",
            program="DPRK",
            entry_details="Possible match: 'Sunrise Holdings Ltd' — similar to 'Sunrise International Holdings' listed for DPRK sanctions evasion. Requires manual verification.",
        )
    ],
}

PEP_DATABASE = {
    "ahmed al-rashidi": PEPRecord(
        is_pep=True, pep_type="DIRECT", pep_tier=2,
        role="Minister of Finance, Federal Republic of Nigeria (2019-2023)",
        country="NG", active=False, risk_level="HIGH",
    ),
    "margaret collins": PEPRecord(
        is_pep=True, pep_type="DIRECT", pep_tier=3,
        role="Elected Local Councillor, Surrey County Council (2015-2022)",
        country="GB", active=False, risk_level="LOW",
    ),
}

ADVERSE_MEDIA_DATABASE = {
    "fasttrack finance ltd": [
        AdverseMediaHit(
            source="FCA Register / FT",
            headline="FCA opens investigation into FastTrack Finance for suspected mis-selling",
            date="2024-01-14",
            category="fraud",
            summary="FCA announced formal investigation into FastTrack Finance Ltd for suspected systematic mis-selling of structured products to retail customers. Estimated £12M customer harm.",
        ),
        AdverseMediaHit(
            source="Companies House / The Guardian",
            headline="FastTrack Finance director disqualified — 6 previous company failures",
            date="2023-09-08",
            category="financial_crime",
            summary="Lead director Ian Fletcher disqualified from acting as company director for 8 years following 6 company insolvencies. Pattern of phoenixing alleged.",
        ),
    ],
    "atlas trading international": [
        AdverseMediaHit(
            source="Reuters",
            headline="Atlas Trading International linked to Ukraine sanctions circumvention network",
            date="2023-11-22",
            category="sanctions_breach",
            summary="Investigative reporting links Atlas Trading International to a network of shell companies used to route payments to sanctioned Russian entities via UAE intermediaries.",
        ),
    ],
}

COMPANY_REGISTRY = {
    "sunrise holdings ltd": CompanyRegistryData(
        registered_name="Sunrise Holdings Ltd",
        registration_number="BVI-2019-44821",
        jurisdiction="British Virgin Islands",
        incorporation_date="2019-03-15",
        status="active",
        directors=["Chen Wei", "Unknown Director (nominee)"],
        beneficial_owners=[],
        ownership_transparency="OPAQUE",
        registered_address="Offshore Chambers, Road Town, Tortola, BVI",
    ),
    "fasttrack finance ltd": CompanyRegistryData(
        registered_name="FastTrack Finance Ltd",
        registration_number="12847391",
        jurisdiction="England & Wales",
        incorporation_date="2018-06-20",
        status="active",
        directors=["Ian Fletcher", "Sandra Osei"],
        beneficial_owners=["Ian Fletcher (75%)"],
        ownership_transparency="HIGH",
        registered_address="14 Canary Wharf, London E14 5AB",
    ),
    "atlas trading international": CompanyRegistryData(
        registered_name="Atlas Trading International Ltd",
        registration_number="UAE-DIC-20211102",
        jurisdiction="UAE (DIFC)",
        incorporation_date="2021-11-02",
        status="active",
        directors=["Mikhail Voronov", "Alexei Karpov", "Lisa Chen"],
        beneficial_owners=["Mikhail Voronov (60%)", "Unknown (40% via Cayman SPV)"],
        ownership_transparency="LOW",
        registered_address="Gate Building, East Wing, DIFC, Dubai",
    ),
    "greenfield advisory partners": CompanyRegistryData(
        registered_name="Greenfield Advisory Partners LLP",
        registration_number="OC421892",
        jurisdiction="England & Wales",
        incorporation_date="2016-04-11",
        status="active",
        directors=["James Thornton", "Rachel Thornton"],
        beneficial_owners=["James Thornton (100%)"],
        ownership_transparency="HIGH",
        registered_address="22 Bedford Row, London WC1R 4JS",
    ),
}

COUNTRY_RISK = {
    "NG": GeographicRisk(country="Nigeria", fatf_status="GREYLIST", corruption_perception_index=24, risk_level="HIGH", notes="FATF greylisted 2023. CPI 24/100. High financial crime risk."),
    "RU": GeographicRisk(country="Russia", fatf_status="BLACKLIST", corruption_perception_index=26, risk_level="CRITICAL", notes="FATF suspended membership 2023. Comprehensive sanctions (OFAC, HMT, EU)."),
    "AZ": GeographicRisk(country="Azerbaijan", fatf_status="CLEAN", corruption_perception_index=23, risk_level="MEDIUM", notes="CPI 23/100. Some AML concerns. Not FATF-listed."),
    "GB": GeographicRisk(country="United Kingdom", fatf_status="CLEAN", corruption_perception_index=71, risk_level="LOW", notes="FATF member in good standing. CPI 71/100."),
    "AE": GeographicRisk(country="UAE", fatf_status="GREYLIST", corruption_perception_index=67, risk_level="MEDIUM", notes="FATF greylisted 2022, enhanced monitoring. CPI 67/100. Significant sanctions evasion risk."),
    "BVI": GeographicRisk(country="British Virgin Islands", fatf_status="CLEAN", corruption_perception_index=None, risk_level="HIGH", notes="UK Overseas Territory but high opacity risk. No public beneficial ownership register."),
    "KY": GeographicRisk(country="Cayman Islands", fatf_status="CLEAN", corruption_perception_index=None, risk_level="HIGH", notes="Major offshore financial centre. Limited beneficial ownership transparency."),
}


# ── Tool definitions ───────────────────────────────────────────────────────────

ENRICHMENT_TOOLS = [
    {
        "name": "search_sanctions_lists",
        "description": "Search OFAC, UN Consolidated, HM Treasury, and EU sanctions lists for the entity name. Returns any matches with match type (exact/fuzzy) and confidence score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to search (individual or company)"},
                "entity_type": {"type": "string", "enum": ["individual", "company"]},
            },
            "required": ["name", "entity_type"],
        },
    },
    {
        "name": "check_pep_status",
        "description": "Check whether an individual is a Politically Exposed Person (PEP) or close associate. Returns PEP tier, role, country, and risk level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "country": {"type": "string", "description": "Country of residence or nationality (ISO 3166-1 alpha-2)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "search_adverse_media",
        "description": "Search news sources, court records, and regulatory announcements for adverse media. Categories: financial_crime, corruption, sanctions_breach, fraud, other.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "entity_type": {"type": "string", "enum": ["individual", "company"]},
            },
            "required": ["name", "entity_type"],
        },
    },
    {
        "name": "lookup_company_registry",
        "description": "Look up company in Companies House (UK) or international corporate registries. Returns directors, beneficial owners, ownership transparency, and registration status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "jurisdiction": {"type": "string", "description": "Country/jurisdiction of incorporation"},
            },
            "required": ["company_name"],
        },
    },
    {
        "name": "assess_geographic_risk",
        "description": "Assess the AML/financial crime risk of a country. Returns FATF status (BLACKLIST/GREYLIST/CLEAN), Corruption Perception Index score, and risk level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "country_code": {"type": "string", "description": "ISO 3166-1 alpha-2 country code"},
            },
            "required": ["country_code"],
        },
    },
]


# ── Tool execution ─────────────────────────────────────────────────────────────

def _execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "search_sanctions_lists":
        name_key = tool_input["name"].lower().strip()
        hits = SANCTIONS_DATABASE.get(name_key, [])
        if not hits:
            return json.dumps({"result": "NO_MATCH", "message": f"No sanctions matches found for '{tool_input['name']}'."})
        return json.dumps({"result": "MATCH", "hits": [h.model_dump() for h in hits]})

    elif tool_name == "check_pep_status":
        name_key = tool_input["name"].lower().strip()
        record = PEP_DATABASE.get(name_key)
        if not record:
            return json.dumps({"is_pep": False, "message": "No PEP record found."})
        return json.dumps(record.model_dump())

    elif tool_name == "search_adverse_media":
        name_key = tool_input["name"].lower().strip()
        hits = ADVERSE_MEDIA_DATABASE.get(name_key, [])
        if not hits:
            return json.dumps({"result": "NO_HITS", "message": "No adverse media found."})
        return json.dumps({"result": "HITS_FOUND", "count": len(hits), "items": [h.model_dump() for h in hits]})

    elif tool_name == "lookup_company_registry":
        name_key = tool_input["company_name"].lower().strip()
        data = COMPANY_REGISTRY.get(name_key)
        if not data:
            return json.dumps({"result": "NOT_FOUND", "message": "Company not found in registry. May require manual lookup."})
        return json.dumps(data.model_dump())

    elif tool_name == "assess_geographic_risk":
        code = tool_input["country_code"].upper()
        risk = COUNTRY_RISK.get(code)
        if not risk:
            return json.dumps({"country_code": code, "risk_level": "MEDIUM", "notes": "No specific intelligence — apply standard FATF framework."})
        return json.dumps(risk.model_dump())

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ── Agent ──────────────────────────────────────────────────────────────────────

def run(
    case_id: str,
    entity_name: str,
    entity_type: EntityType,
    country: str,
    additional_context: dict | None = None,
) -> EnrichedEntity:
    """Run entity enrichment via agentic tool-use loop."""

    context_str = json.dumps(additional_context or {})
    messages = [
        {
            "role": "user",
            "content": f"""Screen this entity for KYC/AML purposes.

Case ID: {case_id}
Entity Name: {entity_name}
Entity Type: {entity_type.value}
Country: {country}
Additional context: {context_str}

Use all relevant tools to conduct a thorough enrichment:
- Search sanctions lists (always)
- Check PEP status (individuals always; for companies check directors)
- Search adverse media (always)
- Look up company registry (companies always)
- Assess geographic risk for the entity's country

Be thorough. If you find a partial match on sanctions, investigate further.
If you find PEP status, assess the risk tier carefully.""",
        }
    ]

    enrichment_data: dict = {
        "sanctions_hits": [],
        "pep_record": None,
        "adverse_media": [],
        "company_registry": None,
        "geographic_risks": [],
        "enrichment_notes": "",
    }

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=(
                "You are a KYC/AML compliance analyst conducting entity due diligence. "
                "Use the available tools to screen the entity thoroughly. "
                "Be methodical: screen sanctions, check PEP, search adverse media, "
                "verify company registry (if applicable), and assess geographic risk."
            ),
            tools=ENRICHMENT_TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            # Agent finished — extract any summary notes from final text
            for block in response.content:
                if hasattr(block, "text"):
                    enrichment_data["enrichment_notes"] = block.text[:500]
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

                # Parse results into enrichment data
                parsed = json.loads(result)
                if block.name == "search_sanctions_lists" and parsed.get("result") == "MATCH":
                    for hit in parsed.get("hits", []):
                        enrichment_data["sanctions_hits"].append(SanctionsHit(**hit))
                elif block.name == "check_pep_status" and parsed.get("is_pep"):
                    enrichment_data["pep_record"] = PEPRecord(**{k: v for k, v in parsed.items() if k != "message"})
                elif block.name == "search_adverse_media" and parsed.get("result") == "HITS_FOUND":
                    for item in parsed.get("items", []):
                        enrichment_data["adverse_media"].append(AdverseMediaHit(**item))
                elif block.name == "lookup_company_registry" and parsed.get("result") != "NOT_FOUND":
                    if "registered_name" in parsed:
                        enrichment_data["company_registry"] = CompanyRegistryData(**parsed)
                elif block.name == "assess_geographic_risk" and "risk_level" in parsed:
                    enrichment_data["geographic_risks"].append(GeographicRisk(**{
                        "country": parsed.get("country", country),
                        "fatf_status": parsed.get("fatf_status", "CLEAN"),
                        "corruption_perception_index": parsed.get("corruption_perception_index"),
                        "risk_level": parsed.get("risk_level", "MEDIUM"),
                        "notes": parsed.get("notes", ""),
                    }))

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return EnrichedEntity(
        case_id=case_id,
        entity_name=entity_name,
        entity_type=entity_type,
        sanctions_hits=enrichment_data["sanctions_hits"],
        pep_record=enrichment_data["pep_record"],
        adverse_media=enrichment_data["adverse_media"],
        company_registry=enrichment_data["company_registry"],
        geographic_risks=enrichment_data["geographic_risks"],
        enrichment_notes=enrichment_data["enrichment_notes"],
    )
