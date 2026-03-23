"""
SYSTVETAM — Crew Seed Script
Zentraux Group LLC

Seeds all 16 crew members into the database from the canonical roster.
Source of truth: Engineering Directive v1.0 file structure + ZOS v1.1 Appendix D
+ Addendum v1.1 department floor mapping.

Idempotent: skips any callsign that already exists.

Usage:
  make seed
  — or —
  docker exec -it systvetam-dispatch python -m scripts.seed_crew
  — or —
  python scripts/seed_crew.py  (with DATABASE_URL in env)
"""

import asyncio
import logging
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Ensure dispatch package is importable
sys.path.insert(0, "/app")

from dispatch.config import settings
from dispatch.database import async_session_factory, engine
from dispatch.models.crew_member import CrewMember, CrewStatus, ExecutionPlane

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("seed_crew")


# ---------------------------------------------------------------------------
# Canonical Crew Roster — 16 operators
#
# Source: Engineering Directive v1.0 agent-mesh/crew/ file list
#         ZOS v1.1 Appendix D — AGT Registry
#         Addendum v1.1 — Department floor mapping
# ---------------------------------------------------------------------------

CREW_ROSTER: list[dict] = [
    # === HQ / Strategy & Governance ===
    {
        "callsign": "tori-delgado",
        "display_name": "Victoria 'Tori' Langford",
        "role": "Board Director / Governance QA",
        "department": "GOVERNANCE",
        "execution_plane": "cloud",
        "sop_reference": "L0-GOVERNANCE",
        "bio": "Board-level governance authority. Co-equal with Levi on Major/Emergency escalations. Owns doctrine compliance and QA sign-off.",
    },
    {
        "callsign": "nova-sterling",
        "display_name": "Dr. Isabella 'NOVA' Reyes",
        "role": "Chief Strategy Officer",
        "department": "STRATEGY",
        "execution_plane": "cloud",
        "sop_reference": "L0-STRATEGY",
        "bio": "Strategic direction and market positioning. Owns competitive analysis, category definition, and board interface.",
    },
    {
        "callsign": "maestra-voss",
        "display_name": "Maestra Voss",
        "role": "Doctrine Architect / Governance Enforcer",
        "department": "GOVERNANCE",
        "execution_plane": "cloud",
        "sop_reference": "L0-GOVERNANCE",
        "bio": "Governance enforcement and doctrine integrity. Ensures all operations meet ZOS standards.",
    },

    # === Engineering Core ===
    {
        "callsign": "marcus-reed",
        "display_name": "Marcus Reed",
        "role": "CTO / Lead Architect",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-ENG-001",
        "bio": "Engineering authority. Owns all system architecture, code review, and technical direction. Escalation path: → Levi.",
    },
    {
        "callsign": "sophia-navarro",
        "display_name": "Sophia Navarro",
        "role": "Platform Engineer / Design Authority",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-ENG-001",
        "bio": "Frontend architecture, design system, and UX authority. ZEN-CIRCUIT token system owner. Escalation: → Marcus.",
    },
    {
        "callsign": "jax-harlow",
        "display_name": "Jaxon 'Jax' Harlow",
        "role": "Sr. AI/ML Engineer / Security Reviewer",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-ENG-001",
        "bio": "AI/ML engineering and rolling security review on all builds. Owns model selection and inference optimization. Escalation: → Marcus.",
    },
    {
        "callsign": "riley-chen",
        "display_name": "Riley Chen",
        "role": "QA Gate Engineer",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-008",
        "bio": "QA gate authority. No build advances past QA without Riley sign-off. Owns test coverage, SOP-008 evaluation, and receipt bundle prep.",
    },
    {
        "callsign": "noah-prescott",
        "display_name": "Dr. Noah Prescott",
        "role": "AI Research Lead / Spec Author",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-ENG-001",
        "bio": "Research direction and specification authorship. Translates intelligence briefs into engineering specs. Escalation: → Marcus.",
    },
    {
        "callsign": "rye-callahan",
        "display_name": "Rye Callahan",
        "role": "DevOps / Infrastructure Engineer",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-INFRA-001",
        "bio": "Infrastructure authority. Docker, Railway, Cloudflare tunnel, CI/CD. Owns deployment pipeline and container orchestration.",
    },
    {
        "callsign": "len-zhao",
        "display_name": "Lena 'Len' Zhao",
        "role": "QA Verification Lead",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-008",
        "bio": "QA verification and test automation. Partners with Riley on gate evaluations. Owns regression testing and hallucination detection.",
    },

    # === Intelligence Core ===
    {
        "callsign": "clyde-nakamura",
        "display_name": "Clyde Nakamura",
        "role": "Market Intelligence Engine / Hacker",
        "department": "INTELLIGENCE",
        "execution_plane": "cloud",
        "container_port": 8006,
        "sop_reference": "SOP-INTEL-001",
        "bio": "Eyes on the street. Runs continuous scraping ops, classifies friction signals, generates Opportunity Briefs. Ships fast, fails cheap, scales what works.",
    },

    # === GTM Engine ===
    {
        "callsign": "jordan-reese",
        "display_name": "Jordan Reese",
        "role": "Head of Commercial / Closer",
        "department": "GTM",
        "execution_plane": "cloud",
        "sop_reference": "SOP-GTM-001",
        "bio": "Revenue authority. Owns pipeline, outreach, deal close. Escalation: → Levi. Voice clips via ElevenLabs. Territory: Arizona first.",
    },
    {
        "callsign": "taylor-moss",
        "display_name": "Taylor Moss",
        "role": "Sales & GTM Lead / Content Strategist",
        "department": "GTM",
        "execution_plane": "cloud",
        "sop_reference": "SOP-GTM-001",
        "bio": "Demand generation and proof asset creation. MQL handoff packages, case studies, LinkedIn ABM campaigns. Escalation: → Jordan.",
    },

    # === Delivery & Customer ===
    {
        "callsign": "alex-harris",
        "display_name": "Alex Harris",
        "role": "Head of Delivery & Operations / Support",
        "department": "DELIVERY",
        "execution_plane": "cloud",
        "sop_reference": "SOP-DELIVERY-001",
        "bio": "Client engagement lifecycle. Technical support, incident management, knowledge base. First responder for customer-facing issues.",
    },

    # === Finance & Admin Ops ===
    {
        "callsign": "maya-lin",
        "display_name": "Maya Lin",
        "role": "Customer Success Lead / Financial Analyst",
        "department": "FINANCE",
        "execution_plane": "cloud",
        "sop_reference": "SOP-FIN-001",
        "bio": "Customer success and financial analysis. Owns churn prevention, usage analytics, and MRR reporting.",
    },
    {
        "callsign": "kim-sato",
        "display_name": "Kimberly 'Kim' Sato",
        "role": "Finance & Admin Ops",
        "department": "FINANCE",
        "execution_plane": "cloud",
        "sop_reference": "SOP-FIN-001",
        "bio": "Financial controls, vendor compliance, Stripe receipting. Owns margin protection and runway management.",
    },
]


# ---------------------------------------------------------------------------
# Seed Logic
# ---------------------------------------------------------------------------

async def seed_crew():
    """Insert all crew members. Skip any that already exist by callsign."""
    async with async_session_factory() as session:
        inserted = 0
        skipped = 0

        for member_data in CREW_ROSTER:
            # Check if callsign already exists
            result = await session.execute(
                select(CrewMember).where(
                    CrewMember.callsign == member_data["callsign"]
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info("SKIP  %s — already exists", member_data["callsign"])
                skipped += 1
                continue

            # Resolve execution plane enum
            plane = ExecutionPlane(member_data.get("execution_plane", "cloud"))

            crew_member = CrewMember(
                callsign=member_data["callsign"],
                display_name=member_data["display_name"],
                role=member_data["role"],
                department=member_data["department"],
                execution_plane=plane,
                sop_reference=member_data.get("sop_reference"),
                container_port=member_data.get("container_port"),
                container_image=f"systvetam-crew-{member_data['callsign']}",
                status=CrewStatus.IDLE,
                bio=member_data.get("bio"),
            )

            session.add(crew_member)
            logger.info("SEED  %s — %s (%s)",
                        member_data["callsign"],
                        member_data["display_name"],
                        member_data["department"])
            inserted += 1

        await session.commit()

        logger.info("")
        logger.info("=== CREW SEED COMPLETE ===")
        logger.info("Inserted: %d", inserted)
        logger.info("Skipped:  %d", skipped)
        logger.info("Total:    %d", len(CREW_ROSTER))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    logger.info("SYSTVETAM — Crew Seed Script")
    logger.info("Database: %s", settings.DATABASE_URL[:40] + "...")
    logger.info("")
    await seed_crew()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
