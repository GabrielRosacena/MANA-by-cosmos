"""
MANA — Rule-Based Decision Module
Maps topic + sentiment results to actionable LGU recommendations.

Inputs  : cluster_id (str), neg_pct (float 0–100), post_count (int)
Outputs : recommendation (str), rule_id (str), rationale (str)

Priority levels are handled separately by the Random Forest classifier.
This module is responsible for recommendations only.

Rule ordering: first match wins. Life-safety clusters (G, H) have the
lowest thresholds because delayed response carries the highest human cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


# ── Volume tiers ─────────────────────────────────────────────────────────────

HIGH_VOLUME = 10      # ≥ 10 posts → amplifies urgency in recommendation
MODERATE_VOLUME = 5   # 5–9 posts


# ── Rule definition ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Rule:
    rule_id: str
    rationale: str          # human-readable explanation of why the rule fires
    recommendation: str     # actionable LGU instruction
    condition: Callable[[str, float, int], bool]

    def matches(self, cluster_id: str, neg_pct: float, post_count: int) -> bool:
        return self.condition(cluster_id, neg_pct, post_count)


# ── Rule table ────────────────────────────────────────────────────────────────
#
# Format:
#   IF  <condition expressed in plain English as rationale>
#   THEN recommendation = <actionable LGU instruction>
#
# Clusters:
#   cluster-a  Food & NFIs
#   cluster-b  Health / WASH / Mental Health
#   cluster-c  Camp Coordination & Evacuation Management (CCCM)
#   cluster-d  Logistics
#   cluster-e  Emergency Telecommunications
#   cluster-f  Education
#   cluster-g  Search, Rescue & Retrieval  ← lowest threshold (life-safety)
#   cluster-h  Management of Dead & Missing ← lowest threshold (life-safety)

RULES: list[Rule] = [

    # ── Cluster G: Search, Rescue & Retrieval ─────────────────────────────────

    Rule(
        rule_id="R-G1",
        rationale="Rescue/SRR topic AND negative sentiment ≥ 50% — active distress likely",
        recommendation=(
            "Deploy SRR team to the reported area immediately. "
            "Forward distress coordinates to the nearest rescue unit and activate "
            "barangay emergency protocols."
        ),
        condition=lambda c, n, v: c == "cluster-g" and n >= 50,
    ),

    Rule(
        rule_id="R-G2",
        rationale="Rescue/SRR topic AND negative sentiment ≥ 30% AND ≥ 5 posts — multi-source distress",
        recommendation=(
            "Multiple rescue-related reports detected. Validate distress locations, "
            "pre-position SRR assets, and coordinate with NDRRMC for reinforcement."
        ),
        condition=lambda c, n, v: c == "cluster-g" and n >= 30 and v >= MODERATE_VOLUME,
    ),

    Rule(
        rule_id="R-G3",
        rationale="Rescue/SRR topic with low negative sentiment — situational monitoring required",
        recommendation=(
            "Rescue-related activity detected. Alert nearest SRR unit for standby "
            "deployment and monitor for escalating distress calls."
        ),
        condition=lambda c, n, v: c == "cluster-g" and n >= 10,
    ),

    # ── Cluster H: Management of Dead & Missing ───────────────────────────────

    Rule(
        rule_id="R-H1",
        rationale="Missing/MDM topic AND negative sentiment ≥ 50% — active unresolved cases",
        recommendation=(
            "Activate MDM coordination desk. Coordinate with hospitals, barangay officials, "
            "and family tracing teams to verify and register all missing persons."
        ),
        condition=lambda c, n, v: c == "cluster-h" and n >= 50,
    ),

    Rule(
        rule_id="R-H2",
        rationale="Missing/MDM topic AND negative sentiment ≥ 30% AND ≥ 3 posts — multiple cases",
        recommendation=(
            "Multiple missing persons reports detected. Dispatch family tracing team, "
            "update hospital intake registry, and coordinate with DSWD for psychosocial support."
        ),
        condition=lambda c, n, v: c == "cluster-h" and n >= 30 and v >= 3,
    ),

    Rule(
        rule_id="R-H3",
        rationale="Missing/MDM topic with low negative sentiment — early monitoring stage",
        recommendation=(
            "Monitor missing persons reports. Maintain coordination desk readiness "
            "and ensure barangay-level reporting channels are active."
        ),
        condition=lambda c, n, v: c == "cluster-h" and n >= 10,
    ),

    # ── Cluster B: Health / WASH / Nutrition / Mental Health ──────────────────

    Rule(
        rule_id="R-B1",
        rationale="Health topic AND negative sentiment ≥ 60% — probable health emergency",
        recommendation=(
            "Deploy mobile medical team to affected area. Conduct health sweep, "
            "distribute medicines and oral rehydration salts, and enforce water safety protocols."
        ),
        condition=lambda c, n, v: c == "cluster-b" and n >= 60,
    ),

    Rule(
        rule_id="R-B2",
        rationale="Health topic AND negative sentiment ≥ 40% AND ≥ 8 posts — high-volume health complaints",
        recommendation=(
            "High-volume health complaints detected. Activate mobile health units, "
            "conduct barangay-level health screening, and reinforce sanitation checkpoints."
        ),
        condition=lambda c, n, v: c == "cluster-b" and n >= 40 and v >= HIGH_VOLUME,
    ),

    Rule(
        rule_id="R-B3",
        rationale="Health topic AND negative sentiment ≥ 35% — emerging health concern",
        recommendation=(
            "Coordinate health monitoring. Pre-position medical supplies and alert "
            "health centers in affected barangays to increase readiness."
        ),
        condition=lambda c, n, v: c == "cluster-b" and n >= 35,
    ),

    # ── Cluster A: Food & Non-Food Items ──────────────────────────────────────

    Rule(
        rule_id="R-A1",
        rationale="Food/NFI topic AND negative sentiment ≥ 65% — acute food shortage",
        recommendation=(
            "Immediate food and NFI dispatch required. Coordinate with DSWD for rapid "
            "relief distribution. Prioritize families with children, elderly, and PWDs."
        ),
        condition=lambda c, n, v: c == "cluster-a" and n >= 65,
    ),

    Rule(
        rule_id="R-A2",
        rationale="Food/NFI topic AND negative sentiment ≥ 45% AND ≥ 8 posts — widespread shortage",
        recommendation=(
            "Widespread food shortage reports. Activate relief pipeline, "
            "coordinate convoy dispatch, and set up community distribution points."
        ),
        condition=lambda c, n, v: c == "cluster-a" and n >= 45 and v >= HIGH_VOLUME,
    ),

    Rule(
        rule_id="R-A3",
        rationale="Food/NFI topic AND negative sentiment ≥ 35% — emerging relief need",
        recommendation=(
            "Validate relief needs in affected area. Prepare food packs and NFIs "
            "for distribution within the next LGU response cycle."
        ),
        condition=lambda c, n, v: c == "cluster-a" and n >= 35,
    ),

    # ── Cluster C: Camp Coordination, Management & Protection ─────────────────

    Rule(
        rule_id="R-C1",
        rationale="CCCM topic AND negative sentiment ≥ 60% — critical camp conditions",
        recommendation=(
            "Evacuation center conditions are critical. Conduct immediate protection audit, "
            "address sanitation failures, decongest overcrowded sites, and open overflow shelters."
        ),
        condition=lambda c, n, v: c == "cluster-c" and n >= 60,
    ),

    Rule(
        rule_id="R-C2",
        rationale="CCCM topic AND negative sentiment ≥ 40% AND ≥ 5 posts — multiple camp issues",
        recommendation=(
            "Multiple evacuation center complaints detected. Dispatch camp management team, "
            "inspect sanitation and water supply, and activate overflow evacuation sites."
        ),
        condition=lambda c, n, v: c == "cluster-c" and n >= 40 and v >= MODERATE_VOLUME,
    ),

    Rule(
        rule_id="R-C3",
        rationale="CCCM topic AND negative sentiment ≥ 30% — early camp management concern",
        recommendation=(
            "Monitor evacuation center conditions. Conduct barangay-level check on "
            "shelter capacity, basic services, and protection concerns."
        ),
        condition=lambda c, n, v: c == "cluster-c" and n >= 30,
    ),

    # ── Cluster D: Logistics ──────────────────────────────────────────────────

    Rule(
        rule_id="R-D1",
        rationale="Logistics topic AND negative sentiment ≥ 65% — critical supply disruption",
        recommendation=(
            "Critical logistics disruption detected. Activate alternate supply routes immediately, "
            "issue field advisory, and coordinate DPWH road clearing operations."
        ),
        condition=lambda c, n, v: c == "cluster-d" and n >= 65,
    ),

    Rule(
        rule_id="R-D2",
        rationale="Logistics topic AND negative sentiment ≥ 45% AND ≥ 5 posts — multiple route problems",
        recommendation=(
            "Multiple road or supply route problems reported. Reroute relief convoys, "
            "deploy road clearing teams, and update field logistics advisories."
        ),
        condition=lambda c, n, v: c == "cluster-d" and n >= 45 and v >= MODERATE_VOLUME,
    ),

    Rule(
        rule_id="R-D3",
        rationale="Logistics topic AND negative sentiment ≥ 35% — route monitoring required",
        recommendation=(
            "Monitor route status. Pre-clear alternate supply corridors and "
            "issue a precautionary logistics advisory to field teams."
        ),
        condition=lambda c, n, v: c == "cluster-d" and n >= 35,
    ),

    # ── Cluster E: Emergency Telecommunications ───────────────────────────────

    Rule(
        rule_id="R-E1",
        rationale="Telecom topic AND negative sentiment ≥ 65% — possible communications blackout",
        recommendation=(
            "Communications blackout likely. Deploy satellite phone or HF radio "
            "to affected LGU immediately and coordinate with DICT and telcos for signal restoration."
        ),
        condition=lambda c, n, v: c == "cluster-e" and n >= 65,
    ),

    Rule(
        rule_id="R-E2",
        rationale="Telecom topic AND negative sentiment ≥ 40% — telecommunications disruption",
        recommendation=(
            "Telecommunications disruptions reported. Coordinate with telcos for "
            "priority restoration and pre-position backup communication assets in affected areas."
        ),
        condition=lambda c, n, v: c == "cluster-e" and n >= 40,
    ),

    # ── Cluster F: Education ──────────────────────────────────────────────────

    Rule(
        rule_id="R-F1",
        rationale="Education topic AND negative sentiment ≥ 70% AND ≥ 10 posts — major school disruption",
        recommendation=(
            "Significant education disruption detected. Coordinate with DepEd for a class "
            "suspension order and implement temporary distance or modular learning modalities."
        ),
        condition=lambda c, n, v: c == "cluster-f" and n >= 70 and v >= HIGH_VOLUME,
    ),

    Rule(
        rule_id="R-F2",
        rationale="Education topic AND negative sentiment ≥ 50% — school safety concerns",
        recommendation=(
            "Education-related concerns detected. Advise LGU to assess school "
            "structural safety and coordinate with DepEd for contingency class arrangements."
        ),
        condition=lambda c, n, v: c == "cluster-f" and n >= 50,
    ),

    # ── Global volume override ────────────────────────────────────────────────

    Rule(
        rule_id="R-VOL",
        rationale="Any cluster AND negative sentiment ≥ 65% AND ≥ 15 posts — volume spike",
        recommendation=(
            "Abnormally high post volume with majority negative sentiment detected. "
            "Escalate to LGU operations center for immediate cross-sector response assessment."
        ),
        condition=lambda c, n, v: n >= 65 and v >= 15,
    ),

    # ── Global fallback rules ─────────────────────────────────────────────────

    Rule(
        rule_id="R-MED",
        rationale="Any cluster AND negative sentiment ≥ 35% — general distress signal",
        recommendation=(
            "Negative sentiment detected in incoming reports. Monitor the situation, "
            "verify reports at the barangay level, and prepare contingency measures."
        ),
        condition=lambda c, n, v: n >= 35,
    ),

    Rule(
        rule_id="R-LOW",
        rationale="Default — negative sentiment < 35%, no urgent signals",
        recommendation=(
            "Situation is within normal parameters. Continue routine monitoring "
            "and update relevant stakeholders at regular reporting intervals."
        ),
        condition=lambda c, n, v: True,
    ),
]


# ── Public API ────────────────────────────────────────────────────────────────

def evaluate(cluster_id: str, neg_pct: float, post_count: int = 1) -> dict:
    """
    Apply rules in order and return the recommendation for the first match.

    Args:
        cluster_id  : NDRRMC cluster identifier (e.g. "cluster-g")
        neg_pct     : percentage of posts with negative sentiment (0–100)
        post_count  : number of posts in this cluster window (default 1)

    Returns:
        {
            "recommendation": str,
            "rule_id":        str,
            "rationale":      str,
            "inputs": {
                "cluster_id":  str,
                "neg_pct":     float,
                "post_count":  int,
            }
        }
    """
    neg_pct = float(neg_pct or 0)
    post_count = int(post_count or 1)

    for rule in RULES:
        if rule.matches(cluster_id, neg_pct, post_count):
            return {
                "recommendation": rule.recommendation,
                "rule_id": rule.rule_id,
                "rationale": rule.rationale,
                "inputs": {
                    "cluster_id": cluster_id,
                    "neg_pct": round(neg_pct, 2),
                    "post_count": post_count,
                },
            }

    return {
        "recommendation": RULES[-1].recommendation,
        "rule_id": "R-LOW",
        "rationale": RULES[-1].rationale,
        "inputs": {
            "cluster_id": cluster_id,
            "neg_pct": round(neg_pct, 2),
            "post_count": post_count,
        },
    }


def list_rules() -> list[dict]:
    """Return the full rule table as plain dicts (for inspection/documentation)."""
    return [
        {
            "rule_id": r.rule_id,
            "rationale": r.rationale,
            "recommendation": r.recommendation,
        }
        for r in RULES
    ]
