"""Append-only SQLite audit trail for KYC decisions."""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from .models import KYCDecision, EnrichedEntity


class AuditTrail:
    def __init__(self, db_path: str | Path = "kyc_audit.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kyc_decisions (
                    entry_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id         TEXT NOT NULL,
                    entity_name     TEXT NOT NULL,
                    entity_type     TEXT NOT NULL,
                    timestamp_utc   TEXT NOT NULL,
                    ai_decision     TEXT NOT NULL,
                    ai_risk_score   INTEGER NOT NULL,
                    ai_confidence   REAL NOT NULL,
                    requires_hitl   INTEGER NOT NULL,
                    hitl_reason     TEXT,
                    red_flags       TEXT NOT NULL,
                    mitigating      TEXT NOT NULL,
                    reasoning       TEXT NOT NULL,
                    enrichment_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyst_reviews (
                    review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id        INTEGER NOT NULL REFERENCES kyc_decisions(entry_id),
                    analyst_id      TEXT NOT NULL,
                    analyst_decision TEXT NOT NULL,
                    analyst_notes   TEXT,
                    final_outcome   TEXT NOT NULL,
                    reviewed_utc    TEXT NOT NULL,
                    UNIQUE(entry_id)
                )
            """)
            conn.commit()

    def log_ai_decision(
        self,
        case_id: str,
        entity_name: str,
        entity_type: str,
        decision: KYCDecision,
        enriched: EnrichedEntity,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO kyc_decisions
                   (case_id, entity_name, entity_type, timestamp_utc, ai_decision,
                    ai_risk_score, ai_confidence, requires_hitl, hitl_reason,
                    red_flags, mitigating, reasoning, enrichment_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    case_id, entity_name, entity_type,
                    datetime.now(timezone.utc).isoformat(),
                    decision.recommended_action.value,
                    decision.risk_score,
                    decision.confidence,
                    int(decision.requires_hitl),
                    decision.hitl_reason,
                    json.dumps(decision.key_red_flags),
                    json.dumps(decision.mitigating_factors),
                    json.dumps(decision.reasoning),
                    enriched.model_dump_json(),
                ),
            )
            conn.commit()
            return cur.lastrowid

    def log_analyst_review(
        self,
        entry_id: int,
        analyst_id: str,
        analyst_decision: str,
        analyst_notes: str,
        final_outcome: str,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO analyst_reviews
                   (entry_id, analyst_id, analyst_decision, analyst_notes, final_outcome, reviewed_utc)
                   VALUES (?,?,?,?,?,?)""",
                (
                    entry_id, analyst_id, analyst_decision,
                    analyst_notes, final_outcome,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total,
                    AVG(d.ai_confidence) AS avg_confidence,
                    SUM(CASE WHEN d.ai_decision = 'APPROVE' THEN 1 ELSE 0 END) AS approved,
                    SUM(CASE WHEN d.ai_decision = 'ENHANCED_DUE_DILIGENCE' THEN 1 ELSE 0 END) AS edd,
                    SUM(CASE WHEN d.ai_decision = 'REJECT' THEN 1 ELSE 0 END) AS rejected,
                    SUM(CASE WHEN d.ai_decision = 'ESCALATE' THEN 1 ELSE 0 END) AS escalated,
                    SUM(CASE WHEN d.requires_hitl = 1 THEN 1 ELSE 0 END) AS hitl_required,
                    SUM(CASE WHEN r.entry_id IS NOT NULL THEN 1 ELSE 0 END) AS reviewed
                FROM kyc_decisions d
                LEFT JOIN analyst_reviews r ON d.entry_id = r.entry_id
            """).fetchone()
        return {
            "total": row[0],
            "avg_confidence": round(row[1], 3) if row[1] else None,
            "approved": row[2], "edd": row[3],
            "rejected": row[4], "escalated": row[5],
            "hitl_required": row[6], "reviewed": row[7],
        }

    def get_recent(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT d.*, r.analyst_id, r.analyst_decision, r.final_outcome, r.reviewed_utc
                   FROM kyc_decisions d
                   LEFT JOIN analyst_reviews r ON d.entry_id = r.entry_id
                   ORDER BY d.entry_id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_pending_hitl(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT d.* FROM kyc_decisions d
                   LEFT JOIN analyst_reviews r ON d.entry_id = r.entry_id
                   WHERE d.requires_hitl = 1 AND r.entry_id IS NULL
                   ORDER BY d.entry_id""",
            ).fetchall()
        return [dict(r) for r in rows]
