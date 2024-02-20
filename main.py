from flask import Flask, request, render_template
import os.path as osp

app = Flask(__name__)

file_path = "report_data.txt"

# 初始化文件
if not osp.exists(file_path):
    with open(file_path, "w") as file:
        file.write("0,0")


def read_data():
    with open(file_path, "r") as file:
        data = file.read().split(",")
    return int(data[0]), int(data[1])


def write_data(success_count, request_count):
    with open(file_path, "w") as file:
        file.write(f"{success_count},{request_count}")


@app.route("/")
def index():
    total_success, total_request = read_data()
    return render_template(
        "index.html", total_success=total_success, total_request=total_request
    )


@app.route("/success_report")
def success_report():
    count = request.args.get("count", 1, type=int)

    total_success, total_request = read_data()
    total_success += count
    write_data(total_success, total_request)

    return "Success"


@app.route("/request_report")
def request_report():
    count = request.args.get("count", 1, type=int)

    total_success, total_request = read_data()
    total_request += count
    write_data(total_success, total_request)

    return "Success"


if __name__ == "__main__":
    app.run(debug=True)
