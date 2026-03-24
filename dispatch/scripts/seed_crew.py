"""
SYSTVETAM — Crew Seed Script
Zentraux Group LLC

Seeds all 16 crew members into the database from the canonical roster.
Source of truth: ROLE__INDEX__v02.md — canonical callsigns and identities.

Idempotent: skips any callsign that already exists.

Callsigns use canonical format (FORGE, CLOSE, NOVA, etc.) — matching
the agent-mesh CREW_REGISTRY and ROLE__INDEX__v02.md exactly.

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

sys.path.insert(0, "/app")

from dispatch.config import settings
from dispatch.database import async_session_factory, engine
from dispatch.models.crew_member import CrewMember, CrewStatus, ExecutionPlane

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("seed_crew")


# ---------------------------------------------------------------------------
# Canonical Crew Roster — 16 operators
# Source: ROLE__INDEX__v02.md — single source of truth
# Excludes: AGT-001 (FOUNDER/Levi) and ZENTRAUX (Agent Zero Orchestrator)
# ---------------------------------------------------------------------------

CREW_ROSTER: list[dict] = [
    # AGT-002 | NOVA | Strategy
    {
        "callsign": "NOVA",
        "display_name": "Dr. Isabella Reyes",
        "role": "Chief Strategy Officer",
        "department": "STRATEGY",
        "execution_plane": "cloud",
        "sop_reference": "L0-STRATEGY",
        "bio": "Strategic direction and market positioning. Owns competitive analysis, category definition, and board interface. Escalation: → Levi.",
    },
    # AGT-003 | ANCHOR | Governance
    {
        "callsign": "ANCHOR",
        "display_name": "Victoria 'Tori' Langford",
        "role": "Board Director / Governance QA",
        "department": "GOVERNANCE",
        "execution_plane": "cloud",
        "sop_reference": "L0-GOVERNANCE",
        "bio": "Board-level governance authority. Co-equal with Levi on Major/Emergency escalations. Owns doctrine compliance and QA sign-off.",
    },
    # AGT-004 | KIM | Finance
    {
        "callsign": "KIM",
        "display_name": "Kimberly Harlan",
        "role": "Finance & Admin Ops",
        "department": "FINANCE",
        "execution_plane": "cloud",
        "sop_reference": "SOP-FIN-001",
        "bio": "Financial controls, vendor compliance, Stripe receipting. Owns margin protection and runway management.",
    },
    # AGT-005 | FORGE | Engineering
    {
        "callsign": "FORGE",
        "display_name": "Marcus Reed",
        "role": "CTO / Lead Architect",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-ENG-001",
        "bio": "Engineering authority. Owns all system architecture, code review, and technical direction. Model: Claude Opus. Escalation: → Levi.",
    },
    # AGT-006 | JAX | Engineering
    {
        "callsign": "JAX",
        "display_name": "Jaxon Harlow",
        "role": "Sr. AI/ML Engineer / Security Reviewer",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-ENG-001",
        "bio": "AI/ML engineering and rolling security review on all builds. Owns model selection and inference optimization. Escalation: → FORGE.",
    },
    # AGT-007 | FRAME | Engineering
    {
        "callsign": "FRAME",
        "display_name": "Sophia Navarro",
        "role": "Platform Engineer / Design Authority",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-ENG-001",
        "bio": "Frontend architecture, design system, and UX authority. ZEN-CIRCUIT token system owner. Escalation: → FORGE.",
    },
    # AGT-008 | RYE | Security
    {
        "callsign": "RYE",
        "display_name": "Riley Kim",
        "role": "Security Engineer / QA Gate",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-008",
        "bio": "QA gate authority and security review. No build advances past QA without RYE sign-off. Owns test coverage and SOP-008 evaluation.",
    },
    # AGT-009 | LEN | Engineering
    {
        "callsign": "LEN",
        "display_name": "Lena Moreau",
        "role": "QA Verification Lead",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-008",
        "bio": "QA verification and test automation. Partners with RYE on gate evaluations. Owns regression testing and hallucination detection.",
    },
    # AGT-010 | SIGNAL | Engineering
    {
        "callsign": "SIGNAL",
        "display_name": "Dr. Noah Khalil",
        "role": "AI Research Lead / Spec Author",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-ENG-001",
        "bio": "Research direction and specification authorship. Translates intelligence briefs into engineering specs. Escalation: → FORGE.",
    },
    # AGT-011 | MAESTRA | Engineering / AI Systems
    {
        "callsign": "MAESTRA",
        "display_name": "Maia Kline",
        "role": "Doctrine Architect / AI Systems Lead",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "L0-GOVERNANCE",
        "bio": "Governance enforcement and AI systems doctrine integrity. Ensures all operations meet ZOS standards. Escalation: → ANCHOR.",
    },
    # AGT-012 | AXIS | Delivery
    {
        "callsign": "AXIS",
        "display_name": "Alex Harris",
        "role": "Head of Delivery & Operations",
        "department": "DELIVERY",
        "execution_plane": "cloud",
        "sop_reference": "SOP-DELIVERY-001",
        "bio": "Client engagement lifecycle. Technical support, incident management, pilot milestones. First responder for customer-facing issues.",
    },
    # AGT-013 | BRIDGE | Delivery / Customer Success
    {
        "callsign": "BRIDGE",
        "display_name": "Maya Torres",
        "role": "Customer Success Lead",
        "department": "DELIVERY",
        "execution_plane": "cloud",
        "sop_reference": "SOP-DELIVERY-001",
        "bio": "Customer success and retention. Owns churn prevention, usage analytics, and MRR reporting. Escalation: → AXIS.",
    },
    # AGT-014 | CLOSE | GTM
    {
        "callsign": "CLOSE",
        "display_name": "Jordan Reese",
        "role": "Head of Commercial / Closer",
        "department": "GTM",
        "execution_plane": "cloud",
        "sop_reference": "SOP-GTM-001",
        "bio": "Revenue authority. Owns pipeline, outreach, deal close. Voice clips via ElevenLabs. Territory: Arizona first. Escalation: → Levi.",
    },
    # AGT-015 | SPARK | GTM
    {
        "callsign": "SPARK",
        "display_name": "Taylor Morgan",
        "role": "Sales & GTM Lead / Content Strategist",
        "department": "GTM",
        "execution_plane": "cloud",
        "sop_reference": "SOP-GTM-001",
        "bio": "Demand generation and proof asset creation. MQL handoff packages, case studies, LinkedIn ABM campaigns. Escalation: → CLOSE.",
    },
    # AGT-016 | CIPH | Digital / Security
    {
        "callsign": "CIPH",
        "display_name": "Cipher Little",
        "role": "Digital Security & Automation Engineer",
        "department": "ENGINEERING",
        "execution_plane": "cloud",
        "sop_reference": "SOP-008",
        "bio": "Digital infrastructure security, automation pipelines, and platform ops. Owns ZOS Command Mesh security layer.",
    },
    # AGT-017 | SCOPE | Intelligence
    {
        "callsign": "SCOPE",
        "display_name": "Clyde Nevestein",
        "role": "Chief Intelligence Officer",
        "department": "INTELLIGENCE",
        "execution_plane": "cloud",
        "sop_reference": "SOP-INTEL-001",
        "bio": "Eyes on the street. Runs continuous scraping ops, classifies friction signals, generates Opportunity Briefs. Sees what others miss.",
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

            plane = ExecutionPlane(member_data.get("execution_plane", "cloud"))

            crew_member = CrewMember(
                callsign=member_data["callsign"],
                display_name=member_data["display_name"],
                role=member_data["role"],
                department=member_data["department"],
                execution_plane=plane,
                sop_reference=member_data.get("sop_reference"),
                container_image=f"systvetam-crew-{member_data['callsign'].lower()}",
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
        logger.info("Source:   ROLE__INDEX__v02.md (canonical)")


async def main():
    logger.info("SYSTVETAM — Crew Seed Script v2")
    logger.info("Canonical source: ROLE__INDEX__v02.md")
    logger.info("Crew count: 16 (AGT-002 through AGT-017, FOUNDER excluded)")
    logger.info("Database: %s", settings.DATABASE_URL[:40] + "...")
    logger.info("")
    await seed_crew()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
