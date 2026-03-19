from flask import Flask, render_template, request
from datetime import datetime

app = Flask(__name__)

def format_time(minutes):
    minutes %= (24 * 60)
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

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

        results.append({
            "rank": i + 1,
            "time": format_time(bed_time),
            "sleep": f"{c}시간",
            "desc": desc
        })

    return results

def calculate_wake_from_now():
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    cycles = [7.5, 6, 4.5]
    results = []

    for i, c in enumerate(cycles):
        sleep_minutes = int(c * 60)
        wake_time = now_minutes + sleep_minutes

        results.append({
            "rank": i + 1,
            "time": format_time(wake_time),
            "sleep": f"{c}시간"
        })

    return results

def get_now_time():
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M")

@app.route("/", methods=["GET", "POST"])
def index():
    sleep_results = None
    wake_results = None

    if request.method == "POST":
        if "wake_submit" in request.form:
            ampm = request.form["ampm"]
            hour = int(request.form["hour"])
            minute = int(request.form["minute"])

            # 24시간 변환
            if ampm == "PM" and hour != 12:
                hour += 12
            elif ampm == "AM" and hour == 12:
                hour = 0

            wake_time = f"{hour:02d}:{minute:02d}"
            sleep_results = calculate_sleep_times(wake_time)

        elif "now" in request.form:
            wake_results = calculate_wake_from_now()

    return render_template("index.html",
                       sleep_results=sleep_results,
                       wake_results=wake_results,
                       now_time=get_now_time())

if __name__ == "__main__":
    app.run(debug=True)