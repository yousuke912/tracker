import json
import os
import hashlib
import anthropic

CACHE_PATH = os.path.expanduser("~/tracker_classifier_cache.json")

CATEGORIES = {
    "コーディング": ["vs code", "cursor", "xcode", "terminal", "iterm", "warp",
                     "github", "gitlab", "stackoverflow", "localhost"],
    "執筆": ["notion", "obsidian", "word", "pages", "google docs", "ulysses",
              "bear", "typora", "markdown"],
    "会議・通話": ["zoom", "meet", "teams", "slack huddle", "facetime", "discord",
                   "gather", "webex"],
    "調査・リサーチ": ["chrome", "safari", "firefox", "google", "検索", "search",
                      "wikipedia", "qiita", "zenn", "medium"],
    "SNS・雑多": ["twitter", "x.com", "instagram", "facebook", "youtube", "tiktok",
                  "netflix", "line", "メッセージ", "mail", "gmail"],
    "設計・思考": ["miro", "figma", "whimsical", "xmind", "mindnode", "canva",
                   "keynote", "powerpoint", "slides"],
    "管理・事務": ["finder", "calendar", "リマインダー", "todo", "asana", "trello",
                  "jira", "excel"],
}

FOCUS_SCORE_MAP = {
    "コーディング": 90, "執筆": 80, "設計・思考": 75,
    "調査・リサーチ": 55, "管理・事務": 50, "会議・通話": 60,
    "SNS・雑多": 20, "不明": 40,
}

_cache = {}

def _load_cache():
    global _cache
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            _cache = json.load(f)

def _save_cache():
    with open(CACHE_PATH, "w") as f:
        json.dump(_cache, f, ensure_ascii=False, indent=2)

def _cache_key(app, title):
    return hashlib.md5(f"{app}||{title[:80]}".encode()).hexdigest()

def _local_classify(app_name, window_title):
    combined = f"{app_name} {window_title}".lower()
    for category, keywords in CATEGORIES.items():
        if any(kw in combined for kw in keywords):
            return category
    return None

def classify(app_name, window_title, use_api=True):
    _load_cache()
    local = _local_classify(app_name, window_title)
    if local:
        return local, FOCUS_SCORE_MAP.get(local, 40)
    if not use_api:
        return "不明", 40
    key = _cache_key(app_name, window_title)
    if key in _cache:
        c = _cache[key]
        return c["category"], c["focus_score"]
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content":
                f"アプリ「{app_name}」タイトル「{window_title[:100]}」を分類してください。\n"
                f"コーディング/執筆/会議・通話/調査・リサーチ/SNS・雑多/設計・思考/管理・事務/不明\n"
                f"JSONのみ返してください: {{\"category\": \"カテゴリ名\"}}"}]
        )
        text = msg.content[0].text.strip()
        s, e = text.find("{"), text.rfind("}") + 1
        category = json.loads(text[s:e]).get("category", "不明") if s >= 0 else "不明"
    except Exception:
        category = "不明"
    score = FOCUS_SCORE_MAP.get(category, 40)
    _cache[key] = {"category": category, "focus_score": score}
    _save_cache()
    return category, score
