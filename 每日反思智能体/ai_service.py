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
1. 【问题分析】2-3句话总结你对这个问题的理解
2. 【核心洞察】从对话中发现的关键模式或根源（1-2条）
3. 【具体行动】3-5条立即可执行的建议（要具体，不能模糊）
4. 【本周实验】选最容易开始的一个，设计成本周小实验

语气温暖、务实。用中文回答。"""


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
