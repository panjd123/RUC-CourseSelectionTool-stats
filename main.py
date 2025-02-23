from fastapi import FastAPI, HTTPException, Request, Response, Depends, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import sqlite3
from datetime import datetime, timedelta
import os
import secrets
import argparse
import hashlib

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

DB_FILE = "db.sqlite"
SALT = "qj27ig2gibq"
STORED_USERNAME = "admin"
STORED_PASSWORD_HASH = (
    "53f597e6e278cccbd706a45ba5321bfd237df44f5f88384ee5c51a859c9bef22"
)

SESSIONS = {}  # {session_id: {"username": str, "expires": datetime}}


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


class LoginRequest(BaseModel):
    username: str
    password: str


# 计算加盐哈希值
def hash_password(password: str, salt: str = SALT):
    salted_password = password + salt
    return hashlib.sha256(salted_password.encode("utf-8")).hexdigest()


def verify_session(session_id: str = Cookie(None)):
    if not session_id or session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    session = SESSIONS[session_id]
    if session["expires"] < datetime.now():
        del SESSIONS[session_id]
        raise HTTPException(status_code=401, detail="Session expired")
    return session["username"]


@app.get("/script_control")
async def script_control():
    return {
        "message": "使用前建议从 https://ruccourse.panjd.net 查看脚本最近被使用的情况，你可以参考这些信息来决定是否使用脚本。",
        "block": False,
    }


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


@app.get("/request_sum")
async def get_request_sum():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT SUM(request_count) FROM stats")
    row = c.fetchone()
    conn.close()
    return {"request_sum": row[0] or 0}


@app.get("/success_sum")
async def get_success_sum():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT SUM(success_count) FROM stats")
    row = c.fetchone()
    conn.close()
    return {"success_sum": row[0] or 0}


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


@app.get("/admin")
async def admin_page():
    return FileResponse("static/admin.html")


@app.post("/admin/login")
async def login(login_data: LoginRequest, response: Response):
    # 后端计算哈希值
    hashed_password = hash_password(login_data.password)
    if (
        login_data.username != STORED_USERNAME
        or hashed_password != STORED_PASSWORD_HASH
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_id = secrets.token_hex(16)
    SESSIONS[session_id] = {
        "username": login_data.username,
        "expires": datetime.now() + timedelta(days=7),
    }

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=not DEBUG_MODE,
        max_age=7 * 24 * 60 * 60,
    )
    return {"status": "success"}


# 新增轻量会话检查接口
@app.get("/admin/check_session")
async def check_session(username: str = Depends(verify_session)):
    return {"status": "valid", "username": username}


@app.get("/admin/download_db")
async def download_db(username: str = Depends(verify_session)):
    if not os.path.exists(DB_FILE):
        raise HTTPException(status_code=404, detail="Database file not found")
    return FileResponse(
        DB_FILE, filename="db.sqlite", media_type="application/octet-stream"
    )


@app.get("/admin/data")
async def get_data(time_range: str = "all", username: str = Depends(verify_session)):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    query = (
        "SELECT id, uuid, success_count, request_count, timestamp FROM stats WHERE 1=1"
    )
    params = []

    if time_range != "all":
        now = datetime.now()
        if time_range == "1d":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            raise HTTPException(status_code=400, detail="Invalid time range")
        query += " AND timestamp >= ?"
        params.append(start_time.isoformat())

    query += " ORDER BY timestamp DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    return {
        "data": [
            {
                "id": row[0],
                "uuid": row[1],
                "success_count": row[2],
                "request_count": row[3],
                "timestamp": row[4],
            }
            for row in rows
        ]
    }


# 解析命令行参数
parser = argparse.ArgumentParser(
    description="Run the FastAPI server with optional debug mode."
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Run in debug mode (no HTTPS, listen on 0.0.0.0)",
)
args = parser.parse_args()
DEBUG_MODE = args.debug

if __name__ == "__main__":
    import uvicorn

    host = "0.0.0.0" if DEBUG_MODE else "127.0.0.1"
    print(f"Running in {'debug' if DEBUG_MODE else 'production'} mode on {host}:10882")
    uvicorn.run(app, host=host, port=10882, workers=1)
