import requests
from datetime import datetime, timedelta
import random

BASE_URL = "http://localhost:8000"


# 构造稀疏测试数据
def generate_test_data():
    uuid = "test-uuid-123"
    base_date = datetime(2025, 1, 1)  # 从 2025 年开始

    # 每年四个活跃时段：1月、4月、7月、10月，每段 15 天
    periods = [
        (base_date + timedelta(days=0), 15),  # 1月1日-15日
        (base_date + timedelta(days=90), 15),  # 4月1日-15日
        (base_date + timedelta(days=181), 15),  # 7月1日-15日
        (base_date + timedelta(days=273), 15),  # 10月1日-15日
    ]

    for start_date, duration in periods:
        for day in range(duration):
            for hour in range(0, 24, 2):  # 每 2 小时一条数据
                timestamp = start_date + timedelta(days=day, hours=hour)
                success_count = random.randint(0, 5)
                request_count = random.randint(5, 20)

                # 上报成功数
                requests.get(
                    f"{BASE_URL}/success_report?uuid={uuid}&count={success_count}",
                    headers={"X-Timestamp": timestamp.isoformat()},
                )
                # 上报请求数
                requests.get(
                    f"{BASE_URL}/request_report?uuid={uuid}&count={request_count}",
                    headers={"X-Timestamp": timestamp.isoformat()},
                )
                print(
                    f"上报数据: 时间={timestamp}, 成功={success_count}, 请求={request_count}"
                )


# 检查统计数据
def check_stats(interval="1d"):
    response = requests.get(f"{BASE_URL}/stats?interval={interval}")
    if response.status_code == 200:
        data = response.json()["data"]
        print(f"\n统计数据 (间隔: {interval}):")
        for entry in data[:5]:  # 只显示前 5 条，避免输出过多
            print(
                f"时间: {entry['time']}, 成功: {entry['success']}, 请求: {entry['requests']}"
            )
        print(f"总计 {len(data)} 条数据")
    else:
        print(f"获取统计失败: {response.status_code}")


if __name__ == "__main__":
    # 生成测试数据
    print("正在生成测试数据...")
    generate_test_data()

    # 检查不同时间尺度的统计
    check_stats("10m")
    check_stats("1h")
    check_stats("1d")

    print("\n测试完成，请访问 http://localhost:8000 查看图表")
