from flask import Flask, jsonify, render_template
from db import query_today_summary, get_conn
from datetime import datetime

app = Flask(__name__)

def seconds_to_hm(s):
    h, m = divmod(s // 60, 60)
    return f"{h}h {m:02d}m" if h else f"{m}m"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/summary")
def api_summary():
    data = query_today_summary()
    total_sec = sum(a["seconds"] for a in data["apps"])
    apps_out = []
    for a in data["apps"][:10]:
        pct = round(a["seconds"] / total_sec * 100) if total_sec else 0
        apps_out.append({"app": a["app_name"], "screen": a["screen_label"],
                         "seconds": a["seconds"], "hm": seconds_to_hm(a["seconds"]),
                         "pct": pct, "category": a["task_category"] or "不明"})
    cat_total = sum(c["seconds"] for c in data["categories"])
    cats_out = []
    for c in data["categories"]:
        pct = round(c["seconds"] / cat_total * 100) if cat_total else 0
        cats_out.append({"name": c["task_category"] or "不明", "seconds": c["seconds"],
                         "hm": seconds_to_hm(c["seconds"]), "pct": pct})
    hourly_out = {}
    for h in data["hourly"]:
        hour = h["hour"]
        if hour not in hourly_out:
            hourly_out[hour] = {}
        hourly_out[hour][f"{h['screen_label']}:{h['task_category'] or '不明'}"] = h["seconds"]
    focus_out = []
    for f in data["focus_blocks"]:
        focus_out.append({"app": f["app_name"], "category": f["task_category"] or "不明",
                          "start": f["start_ts"][11:16] if f["start_ts"] else "",
                          "end": f["end_ts"][11:16] if f["end_ts"] else "",
                          "hm": seconds_to_hm(f["seconds"]), "score": round(f["avg_score"])})
    screen_total = sum(s["seconds"] for s in data["screens"])
    screens_out = []
    for s in data["screens"]:
        pct = round(s["seconds"] / screen_total * 100) if screen_total else 0
        screens_out.append({"label": s["screen_label"], "seconds": s["seconds"],
                            "hm": seconds_to_hm(s["seconds"]), "pct": pct})
    total_work = sum(a["seconds"] for a in data["apps"])
    max_focus = max((f["seconds"] for f in data["focus_blocks"]), default=0)
    return jsonify({
        "apps": apps_out, "categories": cats_out, "hourly": hourly_out,
        "focus_blocks": focus_out, "screens": screens_out,
        "summary": {"total_work_hm": seconds_to_hm(total_work),
                    "switches": data["switches"], "focus_count": len(data["focus_blocks"]),
                    "max_focus_hm": seconds_to_hm(max_focus)}
    })

@app.route("/api/current")
def api_current():
    with get_conn() as conn:
        row = conn.execute("""
            SELECT app_name, window_title, screen_label, task_category, focus_score
            FROM activity ORDER BY ts DESC LIMIT 1
        """).fetchone()
    return jsonify(dict(row) if row else {})

if __name__ == "__main__":
    print("ダッシュボード起動: http://localhost:5555")
    app.run(host="127.0.0.1", port=5555, debug=False)
