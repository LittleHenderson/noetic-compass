"""cost.py -- signed cost authority (GATE 1A.2 section 9 + 1A.2R fixes).

Every rate and ceiling comes from the SIGNED execution approval; there is no
--hourly-rate argument anywhere, and a caller cannot lower the rate used for
projection. The signed values are stored in PRIVATE fields and exposed as
read-only properties (audit minor: in-process mutation cannot relabel a changed
value as signed). Before the campaign's job phase the WORST-CASE cost of the
COMPLETE remaining frozen schedule is checked, and before each job the
worst-case of that single capped job; a job whose worst case could breach the
signed ceiling is refused before it starts. Durations are REAL monotonic
measurements (audit fix: no invented 0.01h). An actual overrun marks the
campaign FAILED and can never be argued away.
"""
from __future__ import annotations


class CostViolation(RuntimeError):
    pass


class CostAuthority:
    def __init__(self, approval: dict):
        # signed values ONLY, stored privately (read-only properties below)
        self.__max_hourly_rate_usd = float(approval["max_hourly_rate_usd"])
        self.__cost_ceiling_usd = float(approval["cost_ceiling_usd"])
        self.__per_job_cap_hours = float(approval["per_job_wall_clock_cap_hours"])
        self.spent_usd = 0.0
        self.jobs = []
        self.failed = False

    @property
    def max_hourly_rate_usd(self) -> float:
        return self.__max_hourly_rate_usd

    @property
    def cost_ceiling_usd(self) -> float:
        return self.__cost_ceiling_usd

    @property
    def per_job_cap_hours(self) -> float:
        return self.__per_job_cap_hours

    def gate_remaining_schedule(self, remaining_job_count: int) -> None:
        """Refuse the whole campaign if the worst-case cost of ALL remaining
        capped jobs plus what is already spent could breach the signed ceiling
        (audit fix: whole-remaining-schedule projection, not one job)."""
        worst = self.spent_usd + (remaining_job_count * self.__per_job_cap_hours
                                  * self.__max_hourly_rate_usd)
        if worst > self.__cost_ceiling_usd:
            raise CostViolation(
                f"COST_SCHEDULE_REFUSAL: {remaining_job_count} remaining capped "
                f"jobs worst-case {worst:.2f} > signed ceiling "
                f"{self.__cost_ceiling_usd:.2f}")

    def gate_job(self, job_id: str) -> None:
        """Refuse a job whose worst-case cost could breach the signed ceiling."""
        worst_case = self.spent_usd \
            + self.__per_job_cap_hours * self.__max_hourly_rate_usd
        if worst_case > self.__cost_ceiling_usd:
            raise CostViolation(
                f"COST_CEILING_REFUSAL: job {job_id}: spent {self.spent_usd:.2f} "
                f"+ worst-case job "
                f"{self.__per_job_cap_hours * self.__max_hourly_rate_usd:.2f} "
                f"= {worst_case:.2f} > signed ceiling {self.__cost_ceiling_usd:.2f}")

    def record_job(self, job_id: str, wall_clock_hours: float) -> float:
        """Record a REAL measured duration (monotonic clock at the call site)."""
        if wall_clock_hours < 0:
            raise CostViolation(f"NEGATIVE_DURATION: job {job_id}")
        if wall_clock_hours > self.__per_job_cap_hours:
            self.failed = True
            raise CostViolation(
                f"PER_JOB_CAP_BREACH: job {job_id} ran {wall_clock_hours:.4f} h "
                f"> signed cap {self.__per_job_cap_hours:.4f} h; campaign FAILED")
        cost = wall_clock_hours * self.__max_hourly_rate_usd
        self.spent_usd += cost
        self.jobs.append({"job_id": job_id, "wall_clock_hours": wall_clock_hours,
                          "measured_cost_usd": cost})
        if self.spent_usd > self.__cost_ceiling_usd:
            self.failed = True
            raise CostViolation(
                f"COST_OVERRUN: spent {self.spent_usd:.2f} > ceiling "
                f"{self.__cost_ceiling_usd:.2f}; campaign FAILED")
        return cost

    def report(self) -> dict:
        return {"report_id": "CAMPAIGN_COST_REPORT",
                "signed_max_hourly_rate_usd": self.__max_hourly_rate_usd,
                "signed_cost_ceiling_usd": self.__cost_ceiling_usd,
                "signed_per_job_cap_hours": self.__per_job_cap_hours,
                "measured_spent_usd": round(self.spent_usd, 6),
                "jobs": list(self.jobs),
                "campaign_cost_failed": self.failed}
