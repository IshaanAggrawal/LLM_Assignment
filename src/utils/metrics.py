from dateutil import parser

def calculate_latency(start_str: str, end_str: str) -> float:
    if not start_str or not end_str:
        return 0.0
    try:
        t1 = parser.parse(start_str)
        t2 = parser.parse(end_str)
        return abs((t2 - t1).total_seconds())
    except Exception:
        return 0.0