"""cost.py -- signed cost authority (GATE 1A.2 section 9).

Every rate and ceiling comes from the SIGNED execution approval; there is no
--hourly-rate argument anywhere, and a caller cannot lower the rate used for
projection. Before each job the WORST-CASE remaining campaign cost is computed
(the signed maximum hourly rate times the per-job cap plus already-spent);
a job that could breach the signed ceiling is refused before it starts. An
actual overrun marks the campaign FAILED (it can never be argued away).
"""
from __future__ import annotations


class CostViolation(RuntimeError):
    pass


class CostAuthority:
    def __init__(self, approval: dict):
        # signed values ONLY -- no keyword overrides exist
        self.max_hourly_rate_usd = float(approval["max_hourly_rate_usd"])
        self.cost_ceiling_usd = float(approval["cost_ceiling_usd"])
        self.per_job_cap_hours = float(approval["per_job_wall_clock_cap_hours"])
        self.spent_usd = 0.0
        self.jobs = []
        self.failed = False

    def gate_job(self, job_id: str) -> None:
        """Refuse a job whose worst-case cost could breach the signed ceiling."""
        worst_case = self.spent_usd \
            + self.per_job_cap_hours * self.max_hourly_rate_usd
        if worst_case > self.cost_ceiling_usd:
            raise CostViolation(
                f"COST_CEILING_REFUSAL: job {job_id}: spent {self.spent_usd:.2f} "
                f"+ worst-case job {self.per_job_cap_hours * self.max_hourly_rate_usd:.2f} "
                f"= {worst_case:.2f} > signed ceiling {self.cost_ceiling_usd:.2f}")

    def record_job(self, job_id: str, wall_clock_hours: float) -> float:
        if wall_clock_hours > self.per_job_cap_hours:
            self.failed = True
            raise CostViolation(
                f"PER_JOB_CAP_BREACH: job {job_id} ran {wall_clock_hours:.3f} h "
                f"> signed cap {self.per_job_cap_hours:.3f} h; campaign FAILED")
        cost = wall_clock_hours * self.max_hourly_rate_usd
        self.spent_usd += cost
        self.jobs.append({"job_id": job_id, "wall_clock_hours": wall_clock_hours,
                          "worst_case_cost_usd": cost})
        if self.spent_usd > self.cost_ceiling_usd:
            self.failed = True
            raise CostViolation(
                f"COST_OVERRUN: spent {self.spent_usd:.2f} > ceiling "
                f"{self.cost_ceiling_usd:.2f}; campaign FAILED")
        return cost

    def report(self) -> dict:
        return {"report_id": "CAMPAIGN_COST_REPORT",
                "signed_max_hourly_rate_usd": self.max_hourly_rate_usd,
                "signed_cost_ceiling_usd": self.cost_ceiling_usd,
                "signed_per_job_cap_hours": self.per_job_cap_hours,
                "worst_case_spent_usd": round(self.spent_usd, 6),
                "jobs": list(self.jobs),
                "campaign_cost_failed": self.failed}
