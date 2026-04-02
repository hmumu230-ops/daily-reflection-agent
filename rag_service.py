import os
from config import BASE_DIR

KNOWLEDGE_DIR = os.path.join(BASE_DIR, 'knowledge')

CATEGORY_KEYWORDS = {
    'emotions': [
        '情绪', '焦虑', '压力', '难过', '愤怒', '心情', '抑郁', '烦躁',
        '痛苦', '开心', '快乐', '恐惧', '担心', '害怕', '无力', '空洞',
        '麻木', '崩溃', '委屈', '失落', '悲伤', '心理', '情感', '感受'
    ],
    'relationships': [
        '关系', '朋友', '家人', '父母', '伴侣', '同事', '吵架', '矛盾',
        '冲突', '沟通', '分手', '孤独', '孤立', '被忽视', '不被理解',
        '边界', '相处', '人际', '社交', '信任', '背叛', '误解', '争吵'
    ],
    'time_planning': [
        '时间', '计划', '拖延', '效率', '忙', '任务', '目标', '截止',
        '来不及', '时间不够', '安排', '规划', '优先', '进度', '完不成',
        '拖', '懒', '摆烂', '待办', '日程', '专注', '分心', '精力'
    ],
    'habits': [
        '习惯', '坚持', '戒掉', '养成', '每天', '规律', '作息', '运动',
        '健身', '阅读', '早起', '睡眠', '饮食', '戒烟', '戒酒', '打卡',
        '自律', '放弃', '半途而废', '改变', '行为', '惰性'
    ]
}

KNOWLEDGE_FILES = {
    'emotions': 'emotions.md',
    'relationships': 'relationships.md',
    'time_planning': 'time_planning.md',
    'habits': 'habits.md'
}

CATEGORY_NAMES = {
    'emotions': '情绪管理',
    'relationships': '人际关系',
    'time_planning': '时间规划',
    'habits': '习惯养成'
}


def detect_categories(user_problem: str) -> list[str]:
    matched = []
    problem_lower = user_problem.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in problem_lower:
                if category not in matched:
                    matched.append(category)
                break
    if not matched:
        matched = list(KNOWLEDGE_FILES.keys())
    return matched


def load_knowledge(category: str) -> str:
    filename = KNOWLEDGE_FILES.get(category)
    if not filename:
        return ''
    filepath = os.path.join(KNOWLEDGE_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ''


def retrieve_knowledge(user_problem: str) -> str:
    categories = detect_categories(user_problem)
    sections = []
    for cat in categories:
        content = load_knowledge(cat)
        if content:
            name = CATEGORY_NAMES.get(cat, cat)
            sections.append(f'## 相关知识：{name}\n\n{content}')
    if not sections:
        return ''
    return '\n\n---\n\n'.join(sections)


def retrieve_history(user_id: int, date: str) -> str:
    from datetime import datetime, timedelta
    from models import get_db, _fetchall

    try:
        current = datetime.fromisoformat(date)
    except ValueError:
        return ''

    past_date = (current - timedelta(days=30)).date().isoformat()

    conn = get_db()
    activities = _fetchall(conn,
        '''SELECT date, category, content, time_start, time_end
           FROM activities
           WHERE user_id = ? AND date >= ? AND date < ?
           ORDER BY date DESC, time_start
           LIMIT 50''',
        (user_id, past_date, date))

    reflections = _fetchall(conn,
        '''SELECT date, summary, reflection
           FROM reflections
           WHERE user_id = ? AND date >= ? AND date < ?
           ORDER BY date DESC
           LIMIT 10''',
        (user_id, past_date, date))
    conn.close()

    if not activities and not reflections:
        return ''

    parts = []

    if activities:
        by_date = {}
        for row in activities:
            d = row['date']
            if d not in by_date:
                by_date[d] = []
            by_date[d].append(f"  [{row['time_start']}-{row['time_end']}] [{row['category']}] {row['content']}")

        activity_lines = ['## 用户近期活动记录（过去30天）']
        for d in sorted(by_date.keys(), reverse=True)[:7]:
            activity_lines.append(f'\n**{d}**')
            activity_lines.extend(by_date[d])
        parts.append('\n'.join(activity_lines))

    if reflections:
        reflection_lines = ['## 用户近期反思记录']
        for row in reflections[:5]:
            reflection_lines.append(f'\n**{row["date"]}**')
            reflection_lines.append(f'总结：{row["summary"]}')
            if row['reflection']:
                reflection_lines.append(f'反思：{row["reflection"][:200]}...')
        parts.append('\n'.join(reflection_lines))

    return '\n\n---\n\n'.join(parts)


def build_rag_context(user_id: int, user_problem: str, date: str) -> dict:
    knowledge = retrieve_knowledge(user_problem)
    history = retrieve_history(user_id, date)
    categories = detect_categories(user_problem)

    return {
        'knowledge': knowledge,
        'history': history,
        'categories': [CATEGORY_NAMES.get(c, c) for c in categories]
    }
