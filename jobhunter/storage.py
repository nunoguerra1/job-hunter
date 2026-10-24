import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from jobhunter.match import MatchResult
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
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                uid TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                scored_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                uid TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                thread TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                company TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gupy_applications (
                application_id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT NOT NULL,
                workplace TEXT NOT NULL,
                contract TEXT NOT NULL,
                current INTEGER,
                total INTEGER,
                tab TEXT NOT NULL,
                job_uid TEXT NOT NULL,
                seen_at TEXT NOT NULL
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

    def save_score(self, uid: str, result: MatchResult) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO scores (uid, data, scored_at) VALUES (?, ?, ?)",
            (uid, result.model_dump_json(), datetime.now(UTC).isoformat()),
        )
        self.conn.commit()

    def scores(self) -> dict[str, MatchResult]:
        rows = self.conn.execute("SELECT uid, data FROM scores").fetchall()
        return {uid: MatchResult.model_validate_json(data) for uid, data in rows}

    def set_status(self, uid: str, status: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO applications (uid, status, updated_at) VALUES (?, ?, ?)",
            (uid, status, datetime.now(UTC).isoformat()),
        )
        self.conn.commit()

    def statuses(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT uid, status FROM applications").fetchall()
        return dict(rows)

    def clear_status(self, uid: str) -> None:
        self.conn.execute("DELETE FROM applications WHERE uid = ?", (uid,))
        self.conn.commit()

    def add_emails(self, rows: list[dict]) -> int:
        added = 0
        for row in rows:
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO emails (id, thread, sent_at, kind, sender, subject, company)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (row["id"], row["thread"], row["sent_at"], row["kind"], row["sender"],
                 row["subject"], row["company"]),
            )
            added += cursor.rowcount
        self.conn.commit()
        return added

    def emails(self) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT id, thread, sent_at, kind, sender, subject, company FROM emails"
            " ORDER BY sent_at"
        )
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def status_times(self) -> dict[str, str]:
        """Quando cada status foi definido pela última vez (ISO, UTC)."""
        rows = self.conn.execute("SELECT uid, updated_at FROM applications").fetchall()
        return dict(rows)

    def save_gupy_applications(self, rows: list[dict]) -> None:
        now = datetime.now(UTC).isoformat()
        kept = {row["application_id"]: row["job_uid"] for row in self.gupy_applications()}
        for row in rows:
            job_uid = row["job_uid"] or kept.get(row["application_id"], "")
            self.conn.execute(
                "INSERT OR REPLACE INTO gupy_applications (application_id, company, title,"
                " location, workplace, contract, current, total, tab, job_uid, seen_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["application_id"], row["company"], row["title"], row["location"],
                    row["workplace"], row["contract"], row["current"], row["total"],
                    row["tab"], job_uid, now,
                ),
            )
        self.conn.commit()

    def gupy_applications(self) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT application_id, company, title, location, workplace, contract, current,"
            " total, tab, job_uid FROM gupy_applications ORDER BY rowid"
        )
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def link_gupy_application(self, application_id: str, job_uid: str) -> bool:
        cursor = self.conn.execute(
            "UPDATE gupy_applications SET job_uid = ? WHERE application_id = ?",
            (job_uid, application_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0