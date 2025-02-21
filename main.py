from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
from datetime import datetime
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

DB_FILE = "db.sqlite"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT NOT NULL,
        success_count INTEGER DEFAULT 0,
        request_count INTEGER DEFAULT 0,
        timestamp TEXT NOT NULL
    )"""
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON stats(timestamp)")
    conn.commit()
    conn.close()


if not os.path.exists(DB_FILE):
    init_db()


class Report(BaseModel):
    uuid: str
    count: int


@app.get("/success_report")
async def report_success(count: int, uuid: str | None = None, request: Request = None):
    if uuid is None:
        uuid = "Unknown"
    elif uuid == r"{UUID}" or len(uuid) == 0:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    timestamp = request.headers.get("X-Timestamp", datetime.now().isoformat())
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO stats (uuid, success_count, request_count, timestamp) VALUES (?, ?, 0, ?)",
        (uuid, count, timestamp),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/request_report")
async def report_request(count: int, uuid: str | None = None, request: Request = None):
    if uuid is None:
        uuid = "Unknown"
    elif uuid == r"{UUID}" or len(uuid) == 0:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    timestamp = request.headers.get("X-Timestamp", datetime.now().isoformat())
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO stats (uuid, request_count, success_count, timestamp) VALUES (?, ?, 0, ?)",
        (uuid, count, timestamp),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.get("/stats")
async def get_stats(interval: str = "10m"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if interval == "10m":
        c.execute(
            """
            SELECT 
                strftime('%Y-%m-%d %H', timestamp) || ':' || 
                printf('%02d', (CAST(strftime('%M', timestamp) AS INTEGER) / 10) * 10) || ':00' as time_slot,
                SUM(success_count) as success_count,
                SUM(request_count) as request_count
            FROM stats
            GROUP BY 
                strftime('%Y-%m-%d %H', timestamp),
                CAST(strftime('%M', timestamp) AS INTEGER) / 10
            ORDER BY time_slot
        """
        )
    elif interval == "1h":
        c.execute(
            """
            SELECT 
                strftime('%Y-%m-%d %H', timestamp) || ':00:00' as time_slot,
                SUM(success_count) as success_count,
                SUM(request_count) as request_count
            FROM stats
            GROUP BY strftime('%Y-%m-%d %H', timestamp)
            ORDER BY time_slot
        """
        )
    elif interval == "1d":
        c.execute(
            """
            SELECT 
                strftime('%Y-%m-%d', timestamp) || 'T00:00:00' as time_slot,
                SUM(success_count) as success_count,
                SUM(request_count) as request_count
            FROM stats
            GROUP BY strftime('%Y-%m-%d', timestamp)
            ORDER BY time_slot
        """
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported interval")

    rows = c.fetchall()
    conn.close()

    return {
        "data": [
            {"time": row[0], "success": row[1] or 0, "requests": row[2] or 0}
            for row in rows
        ]
    }


@app.get("/")
async def root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=10882, workers=1)
