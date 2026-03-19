from datetime import datetime

def calculate_sleep(start, end):
    fmt = "%H:%M"
    start_time = datetime.strptime(start, fmt)
    end_time = datetime.strptime(end, fmt)

    # 다음날로 넘어가는 경우 처리
    if end_time < start_time:
        end_time = end_time.replace(day=start_time.day + 1)

    sleep_time = end_time - start_time
    hours = sleep_time.seconds // 3600

    return hours

def analyze_sleep(hours):
    if hours < 5:
        return "수면 부족 (위험)"
    elif hours < 7:
        return "수면 부족"
    elif hours <= 9:
        return "적정 수면"
    else:
        return "과다 수면"

def main():
    print("=== 아 잠온다 ===")

    sleep_start = input("취침 시간 입력 (HH:MM): ")
    sleep_end = input("기상 시간 입력 (HH:MM): ")

    hours = calculate_sleep(sleep_start, sleep_end)
    result = analyze_sleep(hours)

    print(f"\n수면 시간: {hours}시간")
    print(f"분석 결과: {result}")

if __name__ == "__main__":
    main()