from openai import OpenAI
from config import QIANWEN_API_KEY, AI_MODEL, AI_BASE_URL


def _get_client():
    if not QIANWEN_API_KEY:
        raise ValueError('请在 .env 文件中设置 QIANWEN_API_KEY')
    return OpenAI(api_key=QIANWEN_API_KEY, base_url=AI_BASE_URL)


def _call(system_prompt, user_content, max_tokens=2000):
    """统一调用入口"""
    client = _get_client()
    response = client.chat.completions.create(
        model=AI_MODEL,
        max_tokens=max_tokens,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user',   'content': user_content}
        ]
    )
    return response.choices[0].message.content


def _call_with_history(system_prompt, messages, max_tokens=2000):
    """带对话历史的调用"""
    client = _get_client()
    all_messages = [{'role': 'system', 'content': system_prompt}] + messages
    response = client.chat.completions.create(
        model=AI_MODEL,
        max_tokens=max_tokens,
        messages=all_messages
    )
    return response.choices[0].message.content


def _format_activities(activities):
    if not activities:
        return '今天暂无活动记录'
    lines = []
    for a in activities:
        time_part = f"[{a['time_start']}-{a['time_end']}] " if a.get('time_start') else ''
        lines.append(f"{time_part}{a['content']}")
    return '\n'.join(lines)


# ===== 引导回顾 =====

SYSTEM_PROMPT_GUIDE = """你是一位善于引导的教练。用户告诉你他想解决的问题，你的任务是通过提问帮助他深入思考。

规则：
- 每次只问一个问题
- 只问开放性问题（不能是「是/否」就能回答的）
- 不给建议，不下判断，不给选项
- 根据用户上一条回答顺势深入追问
- 语气温和、好奇、不评判
- 用中文回答"""


def start_guided_review(activities, user_problem):
    """开始引导，生成第一个问题"""
    formatted = _format_activities(activities)
    return _call(
        system_prompt=SYSTEM_PROMPT_GUIDE,
        user_content=(
            f'我想解决的问题是：{user_problem}\n\n'
            f'今天的活动：\n{formatted}\n\n'
            f'请问我第一个引导问题。'
        ),
        max_tokens=300
    )


def continue_guided_review(activities, messages, user_problem):
    """根据对话历史继续引导"""
    formatted = _format_activities(activities)

    history = [{
        'role': 'user',
        'content': (
            f'我想解决的问题是：{user_problem}\n\n'
            f'今天的活动：\n{formatted}\n\n'
            f'请问我第一个引导问题。'
        )
    }]

    for msg in messages:
        role = 'user' if msg['role'] == 'user' else 'assistant'
        history.append({'role': role, 'content': msg['content']})

    return _call_with_history(
        system_prompt=SYSTEM_PROMPT_GUIDE,
        messages=history,
        max_tokens=300
    )


# ===== 生成建议 =====

SYSTEM_PROMPT_SOLUTION = """你是一位专业的人生教练，擅长从第一性原理出发，结合心理学知识找到问题的根本原因，给出具体可执行的建议。

你会收到：用户的问题、引导对话内容、相关知识、历史数据。

请给出：
1. 问题分析：2-3句话总结你对这个问题的理解
2. 核心洞察：从对话中发现的关键模式或根源（1-2条）
3. 具体行动：3-5条立即可执行的建议（要具体，不能模糊）
4. 本周实验：选最容易开始的一个，设计成本周小实验

格式要求：
- 不要使用任何 markdown 格式（不要用 ** # - 等符号）
- 用自然的中文段落书写，像朋友写信一样
- 每个部分之间用空行隔开
- 语气温暖、务实
- 用中文回答"""


def generate_solution(activities, messages, user_problem, knowledge_context, history_context):
    """综合所有信息生成最终建议"""
    formatted = _format_activities(activities)

    conversation = '\n'.join([
        f"{'用户' if m['role'] == 'user' else 'AI'}：{m['content']}"
        for m in messages
    ])

    parts = [
        f'## 用户的问题\n{user_problem}',
        f'## 今天的活动\n{formatted}',
        f'## 对话内容\n{conversation}',
    ]
    if knowledge_context:
        parts.append(f'## 相关知识\n{knowledge_context}')
    if history_context:
        parts.append(f'## 历史数据\n{history_context}')

    return _call(
        system_prompt=SYSTEM_PROMPT_SOLUTION,
        user_content='\n\n---\n\n'.join(parts),
        max_tokens=2000
    )


# ===== 笔记提炼 =====

SYSTEM_PROMPT_NOTE_SUMMARY = """你是一位善于整理知识的学习助手。用户今天学习了一些内容，以原始笔记的形式提供给你。

你的任务是：
1. 核心要点：提炼今天学到的最重要的 3-5 个知识点（用简洁的一句话概括每条）
2. 知识地图：这些知识点之间有什么联系？构成了什么样的体系？
3. 延伸思考：基于今天所学，你认为有哪 1-2 个值得进一步探索的方向？
4. 一句话总结：用一句话概括今天的学习主题

格式要求：
- 不要使用任何 markdown 格式（不要用 ** # - 等符号）
- 用自然的中文段落，像老师整理板书一样清晰
- 忠实于原始内容，不添加原文中没有的概念
- 用中文回答"""


def generate_note_summary(notes: list) -> str:
    """对当天笔记进行提炼总结，不修改原始内容"""
    parts = ['以下是用户今天的原始学习笔记：\n']
    for note in notes:
        parts.append(f'--- 文件：{note["name"]} ---')
        parts.append(note['text'])
        parts.append('')
    return _call(
        system_prompt=SYSTEM_PROMPT_NOTE_SUMMARY,
        user_content='\n'.join(parts),
        max_tokens=1500
    )


# ===== 每周总结 =====

SYSTEM_PROMPT_WEEKLY = """你是一位专业的心理咨询师和人生教练，擅长从一周的对话记录中识别深层模式。

你会收到用户一周内所有的反思对话（包括他们提出的问题、和AI的对话过程、最终的建议）。

请从以下维度分析这一周：

1. 情绪轨迹
   回顾这一周用户的情绪变化，从周一到周日经历了怎样的起伏，用温暖的语言描述

2. 行动复盘
   用户这周实际做了什么、面对了哪些挑战、有哪些值得肯定的地方

3. 核心模式
   从多次对话中提炼出反复出现的思维模式或行为习惯（好的和需要改善的都说）

4. 趋势预判
   基于这周的表现和历史规律，如果保持当前状态，下周大概率会怎样。同时给出一个更好的可能性——如果做出某个小改变的话

5. 下周一件事
   只给一条最关键的建议，下周只需要做好这一件事就够了

格式要求：
- 不要使用任何 markdown 格式（不要用 ** # - 等符号）
- 用自然段落书写，像一位老朋友写的信
- 每个部分用标题和空行隔开
- 语气温暖真诚，像在咖啡馆跟朋友聊天
- 用中文回答"""


def generate_weekly_summary(sessions_data, knowledge_context='', history_context='', notes_by_date=None):
    """生成每周总结"""
    parts = ['以下是用户这一周的所有反思对话记录：\n']

    for session in sessions_data:
        date = session.get('date', '未知日期')
        problem = session.get('problem', '')
        status = session.get('status', '')

        parts.append(f'--- {date} ---')
        parts.append(f'问题：{problem}')

        if session.get('history'):
            for msg in session['history']:
                role = '用户' if msg['role'] == 'user' else 'AI'
                parts.append(f'{role}：{msg["content"]}')

        if session.get('solution'):
            parts.append(f'最终建议：{session["solution"]}')

        parts.append('')

    if notes_by_date:
        parts.append('\n\n以下是用户这一周的学习笔记（请结合笔记内容分析知识成长轨迹）：\n')
        for date_str, notes in sorted(notes_by_date.items()):
            parts.append(f'--- {date_str} 的笔记 ---')
            for note in notes:
                parts.append(f'[{note["name"]}]\n{note["text"][:1000]}')
            parts.append('')

    if knowledge_context:
        parts.append(f'\n相关知识背景：\n{knowledge_context}')
    if history_context:
        parts.append(f'\n历史数据：\n{history_context}')

    return _call(
        system_prompt=SYSTEM_PROMPT_WEEKLY,
        user_content='\n'.join(parts),
        max_tokens=3000
    )


# ===== 保留旧功能（日常反思、趋势分析）=====

def generate_daily_reflection(activities):
    formatted = _format_activities(activities)
    date = activities[0]['date'] if activities else ''
    text = _call(
        system_prompt='你是一位善于反思的人生教练。根据用户的活动记录，给出今日总结和深度反思，语气温暖鼓励，用中文回答。',
        user_content=f'{date} 的活动记录：\n\n{formatted}'
    )
    if '深度反思' in text:
        parts = text.split('深度反思', 1)
        summary = parts[0].strip().lstrip('【今日总结】').strip()
        reflection = parts[1].strip()
    else:
        summary = text[:200]
        reflection = text
    return {'summary': summary, 'reflection': reflection}


def generate_trend_analysis(activities):
    by_date = {}
    for a in activities:
        by_date.setdefault(a['date'], []).append(a)
    lines = []
    for d in sorted(by_date.keys()):
        lines.append(f'\n--- {d} ---')
        lines.append(_format_activities(by_date[d]))
    return _call(
        system_prompt='你是一位善于数据分析的人生教练。分析多天的活动记录，给出整体趋势、亮点和改进建议，用中文回答。',
        user_content='以下是多天的活动记录：\n' + ''.join(lines)
    )
