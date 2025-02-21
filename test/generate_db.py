import sqlite3
from datetime import datetime, timedelta
import random
import os

DB_FILE = "db.sqlite"

# 删除旧数据库
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# 创建数据库和表
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute(
    """CREATE TABLE stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL,
    success_count INTEGER DEFAULT 0,
    request_count INTEGER DEFAULT 0,
    timestamp TEXT NOT NULL
)"""
)
c.execute("CREATE INDEX idx_timestamp ON stats(timestamp)")


# 生成测试数据
def generate_test_data():
    uuid = "test-uuid-123"
    base_date = datetime(2025, 1, 1)
    periods = [
        (base_date + timedelta(days=0), 15),
        (base_date + timedelta(days=90), 15),
        (base_date + timedelta(days=181), 15),
        (base_date + timedelta(days=273), 15),
    ]

    data = []
    for start_date, duration in periods:
        for day in range(duration):
            for hour in range(0, 24, 2):
                timestamp = start_date + timedelta(days=day, hours=hour)
                success_count = random.randint(0, 5)
                request_count = random.randint(5, 20)
                data.append((uuid, success_count, 0, timestamp.isoformat()))
                data.append((uuid, 0, request_count, timestamp.isoformat()))

    c.executemany(
        "INSERT INTO stats (uuid, success_count, request_count, timestamp) VALUES (?, ?, ?, ?)",
        data,
    )
    conn.commit()
    print(f"生成并插入 {len(data)} 条数据到 {DB_FILE}")


if __name__ == "__main__":
    print("正在生成测试数据库...")
    generate_test_data()
    conn.close()
    print("数据库生成完成")
