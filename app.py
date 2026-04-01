from datetime import datetime, timedelta
import json

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import (
    create_user,
    delete_history_item,
    get_history,
    get_history_item,
    get_history_stats,
    get_user_by_id,
    get_user_by_username,
    init_db,
    save_history,
)

app = Flask(__name__)
app.secret_key = "sleep-time-secret-key"
app.permanent_session_lifetime = timedelta(days=30)

SAVE_FILE = "last_input.json"


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def format_time(minutes):
    minutes %= 24 * 60
    hour = minutes // 60
    minute = minutes % 60

    ampm = "오전" if hour < 12 else "오후"
    hour = hour % 12
    if hour == 0:
        hour = 12

    return f"{ampm} {hour:02d}:{minute:02d}"


def calculate_sleep_times(wake_time):
    hour, minute = map(int, wake_time.split(":"))
    wake_minutes = hour * 60 + minute

    cycles = [
        (7.5, "가장 이상적인 수면"),
        (6, "적당한 수면"),
        (4.5, "최소 수면"),
    ]

    results = []

    for rank, (sleep_hours, description) in enumerate(cycles, start=1):
        bed_time = wake_minutes - int(sleep_hours * 60)
        warning = None

        if bed_time < 0:
            bed_time += 24 * 60

        if bed_time >= 2 * 60:
            warning = "너무 늦게 잠들면 피로가 누적될 수 있어요."

        results.append(
            {
                "rank": rank,
                "time": format_time(bed_time),
                "sleep": f"{sleep_hours}시간",
                "desc": description,
                "warning": warning,
            }
        )

    return results


def calculate_wake_from_now():
    now = datetime.now()
    now_minutes = now.hour * 60 + now.minute

    cycles = [
        (7.5, "가장 이상적인 기상"),
        (6, "적당한 기상"),
        (4.5, "최소 수면 기상"),
    ]

    results = []

    for rank, (sleep_hours, description) in enumerate(cycles, start=1):
        wake_minutes = now_minutes + int(sleep_hours * 60)
        results.append(
            {
                "rank": rank,
                "time": format_time(wake_minutes),
                "sleep": f"{sleep_hours}시간",
                "desc": description,
            }
        )

    return results


def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def get_sleep_comment(hours):
    if hours >= 7:
        return "충분한 수면 시간이에요."
    if hours >= 5:
        return "조금 부족한 수면 시간이에요."
    return "수면 시간이 많이 부족해요."


def normalize_minute(minute):
    try:
        return f"{int(minute):02d}"
    except (TypeError, ValueError):
        return str(minute).zfill(2)


def convert_to_24h(ampm, hour, minute):
    hour_24 = int(hour)
    minute_24 = int(minute)

    if ampm == "PM" and hour_24 != 12:
        hour_24 += 12
    elif ampm == "AM" and hour_24 == 12:
        hour_24 = 0

    return f"{hour_24:02d}:{minute_24:02d}"


def build_sleep_result(ampm, hour, minute):
    wake_time = convert_to_24h(ampm, hour, minute)
    return calculate_sleep_times(wake_time), get_sleep_comment(7.5)


def format_ampm_display(ampm, hour, minute):
    return f"{ampm} {int(hour):02d}:{int(minute):02d}"


def build_stats_view(user_id):
    stats = get_history_stats(user_id)

    most_used = "-"
    if stats["most_used_30d"]:
        most_used = format_ampm_display(
            stats["most_used_30d"]["ampm"],
            stats["most_used_30d"]["hour"],
            stats["most_used_30d"]["minute"],
        )

    return {
        "count_7d": stats["count_7d"],
        "count_30d": stats["count_30d"],
        "avg_7d": format_time(stats["avg_7d_minutes"]) if stats["avg_7d_minutes"] is not None else "-",
        "avg_30d": format_time(stats["avg_30d_minutes"]) if stats["avg_30d_minutes"] is not None else "-",
        "most_used_30d": most_used,
    }


def save_last_input(ampm, hour, minute):
    with open(SAVE_FILE, "w", encoding="utf-8") as file:
        json.dump({"ampm": ampm, "hour": hour, "minute": minute}, file)


def load_last_input():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"ampm": "AM", "hour": 7, "minute": "00"}


def get_result_state():
    result_type = session.get("result_type")
    result_data = session.get("result_data")

    if result_type == "sleep":
        return result_data, None, session.get("result_comment")
    if result_type == "wake":
        return None, result_data, None
    return None, None, None


@app.route("/", methods=["GET", "POST"])
def index():
    user = get_current_user()
    if not user:
        return render_template("index.html", auth_mode="login", now_time=get_now())

    data = load_last_input()
    selected_ampm = data.get("ampm", "AM")
    selected_hour = int(data.get("hour", 7))
    selected_minute = normalize_minute(data.get("minute", "00"))

    sleep_results, wake_results, comment = get_result_state()

    if request.method == "POST":
        if "history_pick_id" in request.form:
            try:
                history_id = int(request.form["history_pick_id"])
            except (TypeError, ValueError):
                flash("유효하지 않은 요청입니다.", "error")
                return redirect(url_for("index"))

            history_item = get_history_item(user["id"], history_id)
            if not history_item:
                flash("선택한 기록을 찾을 수 없습니다.", "error")
                return redirect(url_for("index"))

            selected_ampm = history_item["ampm"]
            selected_hour = int(history_item["hour"])
            selected_minute = normalize_minute(history_item["minute"])

            sleep_results, comment = build_sleep_result(
                selected_ampm, selected_hour, selected_minute
            )
            save_last_input(selected_ampm, selected_hour, selected_minute)

            session["result_type"] = "sleep"
            session["result_data"] = sleep_results
            session["result_comment"] = comment
            flash("최근 기록으로 추천 시간을 다시 계산했어요.", "success")
            return redirect(url_for("index"))

        if "history_delete_id" in request.form:
            try:
                history_id = int(request.form["history_delete_id"])
            except (TypeError, ValueError):
                flash("유효하지 않은 요청입니다.", "error")
                return redirect(url_for("index"))

            deleted = delete_history_item(user["id"], history_id)
            if deleted:
                flash("기록을 삭제했어요.", "success")
            else:
                flash("삭제할 기록을 찾지 못했어요.", "error")
            return redirect(url_for("index"))

        if "wake_submit" in request.form:
            selected_ampm = request.form["ampm"]
            selected_hour = int(request.form["hour"])
            selected_minute = normalize_minute(request.form["minute"])
            sleep_results, comment = build_sleep_result(
                selected_ampm, selected_hour, selected_minute
            )

            save_last_input(selected_ampm, selected_hour, selected_minute)
            save_history(user["id"], selected_ampm, selected_hour, selected_minute)

            session["result_type"] = "sleep"
            session["result_data"] = sleep_results
            session["result_comment"] = comment
            return redirect(url_for("index"))

        if "now" in request.form:
            wake_results = calculate_wake_from_now()
            session["result_type"] = "wake"
            session["result_data"] = wake_results
            session.pop("result_comment", None)
            return redirect(url_for("index"))

    history = get_history(user["id"])
    stats = build_stats_view(user["id"])
    return render_template(
        "index.html",
        auth_mode=None,
        current_user=user["username"],
        history=history,
        stats=stats,
        sleep_results=sleep_results,
        wake_results=wake_results,
        now_time=get_now(),
        selected_ampm=selected_ampm,
        selected_hour=selected_hour,
        selected_minute=selected_minute,
        selected_display=format_ampm_display(selected_ampm, selected_hour, selected_minute),
        comment=comment,
    )


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("아이디와 비밀번호를 모두 입력해 주세요.", "error")
        return render_template("index.html", auth_mode="login", now_time=get_now()), 400

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password"], password):
        flash("아이디 또는 비밀번호가 올바르지 않습니다.", "error")
        return render_template("index.html", auth_mode="login", now_time=get_now()), 400

    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    flash(f"{user['username']}님 다시 오셨네요.", "success")
    return redirect(url_for("index"))


@app.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")

    if len(username) < 3:
        flash("아이디는 3자 이상으로 입력해 주세요.", "error")
        return render_template("index.html", auth_mode="signup", now_time=get_now()), 400

    if len(password) < 4:
        flash("비밀번호는 4자 이상으로 입력해 주세요.", "error")
        return render_template("index.html", auth_mode="signup", now_time=get_now()), 400

    if password != password_confirm:
        flash("비밀번호 확인이 일치하지 않습니다.", "error")
        return render_template("index.html", auth_mode="signup", now_time=get_now()), 400

    if get_user_by_username(username):
        flash("이미 사용 중인 아이디입니다.", "error")
        return render_template("index.html", auth_mode="signup", now_time=get_now()), 400

    user_id = create_user(username, generate_password_hash(password))

    session.clear()
    session.permanent = True
    session["user_id"] = user_id
    flash(f"{username}님 회원가입이 완료되었습니다.", "success")
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "success")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
