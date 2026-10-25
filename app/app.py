import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg
from psycopg.rows import dict_row


def connect_db():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        row_factory=dict_row,
        connect_timeout=3,
    )


def initialize_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
            return

        if self.path == "/notes":
            try:
                with connect_db() as conn:
                    rows = conn.execute(
                        "SELECT id, content, created_at FROM notes ORDER BY id"
                    ).fetchall()
                self.send_json(200, {"notes": rows})
            except Exception:
                self.send_json(500, {"error": "Database request failed"})
            return

        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/notes":
            self.send_json(404, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 10000:
                self.send_json(400, {"error": "Invalid request size"})
                return

            data = json.loads(self.rfile.read(length))
            content = data.get("content")

            if not isinstance(content, str) or not content.strip():
                self.send_json(400, {"error": "content is required"})
                return

            with connect_db() as conn:
                note = conn.execute(
                    "INSERT INTO notes (content) VALUES (%s) "
                    "RETURNING id, content, created_at",
                    (content.strip(),),
                ).fetchone()

            self.send_json(201, {"note": note})
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"error": "Invalid JSON"})
        except Exception:
            self.send_json(500, {"error": "Database request failed"})

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    initialize_db()
    print("Notes API listening on port 8000")
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

