from flask import Flask, render_template, request

app = Flask(__name__)

def calculate_times(wake_time):
    h, m = map(int, wake_time.split(":"))
    wake_minutes = h * 60 + m

    cycles = [4.5, 6, 7.5]  # 추천 수면 시간
    results = []

    for c in cycles:
        sleep_minutes = int(c * 60)
        bed_time = wake_minutes - sleep_minutes

        if bed_time < 0:
            bed_time += 24 * 60

        bh = bed_time // 60
        bm = bed_time % 60

        results.append(f"{bh:02d}:{bm:02d} (수면 {c}시간)")

    return results

@app.route("/", methods=["GET", "POST"])
def index():
    results = None

    if request.method == "POST":
        wake_time = request.form["wake"]
        results = calculate_times(wake_time)

    return render_template("index.html", results=results)

if __name__ == "__main__":
    app.run(debug=True)