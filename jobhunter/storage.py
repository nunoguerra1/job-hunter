import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from jobhunter.models import Job


class JobStore:
    def __init__(self, path: str = "data/jobs.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                uid TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                first_seen TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def add_new(self, jobs: list[Job]) -> list[Job]:
        """Salva só as vagas inéditas e devolve quais eram novas."""
        now = datetime.now(UTC).isoformat()
        new_jobs = []
        for job in jobs:
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO jobs (uid, data, first_seen) VALUES (?, ?, ?)",
                (job.uid, job.model_dump_json(), now),
            )
            if cursor.rowcount:
                new_jobs.append(job)
        self.conn.commit()
        return new_jobs

    def all(self) -> list[Job]:
        rows = self.conn.execute("SELECT data FROM jobs ORDER BY first_seen DESC").fetchall()
        return [Job.model_validate_json(row[0]) for row in rows]