from flask import Flask, render_template, request
from datetime import datetime
import json

app = Flask(__name__)

SAVE_FILE = "last_input.json"

# 시간 포맷
def format_time(minutes):
    minutes %= (24 * 60)
    h = minutes // 60
    m = minutes % 60

    ampm = "오전" if h < 12 else "오후"
    h = h % 12
    if h == 0:
        h = 12

    return f"{ampm} {h:02d}:{m:02d}"

# 수면 계산
def calculate_sleep_times(wake_time):
    h, m = map(int, wake_time.split(":"))
    wake_minutes = h * 60 + m

    cycles = [
        (7.5, "⭐ 가장 이상적인 수면"),
        (6, "👍 적당한 수면"),
        (4.5, "⚠️ 최소 수면")
    ]

    results = []

    for i, (c, desc) in enumerate(cycles):
        sleep_minutes = int(c * 60)
        bed_time = wake_minutes - sleep_minutes

        if bed_time < 0:
            bed_time += 24 * 60

        warning = None
        if bed_time >= (2 * 60):  # 새벽 2시 이후
            warning = "⚠️ 너무 늦게 자면 피로가 누적될 수 있습니다"

        results.append({
            "rank": i + 1,
            "time": format_time(bed_time),
            "sleep": f"{c}시간",
            "desc": desc,
            "warning": warning
        })

    return results

# 지금 자면
def calculate_wake_from_now():
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    cycles = [
        (7.5, "⭐ 가장 이상적인 기상"),
        (6, "👍 적당한 기상"),
        (4.5, "⚠️ 최소 기상")
    ]

    results = []

    for i, (c, desc) in enumerate(cycles):
        wake_time = now_minutes + int(c * 60)

        results.append({
            "rank": i + 1,
            "time": format_time(wake_time),
            "sleep": f"{c}시간",
            "desc": desc
        })

    return results

# 현재 시간
def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# 수면 평가
def get_sleep_comment(hours):
    if hours >= 7:
        return "👍 충분한 수면입니다"
    elif hours >= 5:
        return "⚠️ 약간 부족한 수면입니다"
    else:
        return "❗ 수면 부족 위험"

# 저장
def save_last_input(ampm, hour, minute):
    with open(SAVE_FILE, "w") as f:
        json.dump({
            "ampm": ampm,
            "hour": hour,
            "minute": minute
        }, f)

# 불러오기
def load_last_input():
    try:
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"ampm": "AM", "hour": 7, "minute": "00"}


@app.route("/", methods=["GET", "POST"])
def index():
    data = load_last_input()
    selected_ampm = data["ampm"]
    selected_hour = data["hour"]
    selected_minute = data["minute"]

    sleep_results = None
    wake_results = None
    comment = None

    if request.method == "POST":
        if "wake_submit" in request.form:
            selected_ampm = request.form["ampm"]
            selected_hour = int(request.form["hour"])
            selected_minute = request.form["minute"]

            hour = selected_hour
            minute = int(selected_minute)

            if selected_ampm == "PM" and hour != 12:
                hour += 12
            elif selected_ampm == "AM" and hour == 12:
                hour = 0

            wake_time = f"{hour:02d}:{minute:02d}"
            sleep_results = calculate_sleep_times(wake_time)

            comment = get_sleep_comment(7.5)

            save_last_input(selected_ampm, selected_hour, selected_minute)

        elif "now" in request.form:
            wake_results = calculate_wake_from_now()

    return render_template("index.html",
        sleep_results=sleep_results,
        wake_results=wake_results,
        now_time=get_now(),
        selected_ampm=selected_ampm,
        selected_hour=selected_hour,
        selected_minute=selected_minute,
        selected_display=f"{selected_ampm} {selected_hour}:{selected_minute}",
        comment=comment
    )

if __name__ == "__main__":
    app.run(debug=True)