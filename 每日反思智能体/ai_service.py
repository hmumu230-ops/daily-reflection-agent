import anthropic
from config import ANTHROPIC_API_KEY, AI_MODEL

SYSTEM_PROMPT_REFLECTION = """你是一位善于反思与洞察的人生教练。用户会提供一天的活动记录，包含四个类别：
身心活动、意识活动、精神活动、行为活动。

请提供：
1. 【今日总结】简要概述这一天的活动特点（2-3句话）
2. 【深度反思】从以下角度进行反思：
   - 四类活动的时间分配是否均衡
   - 哪些活动体现了积极的生活态度
   - 哪些方面可以改进
   - 明天可以尝试的一个小改变

用温暖、鼓励的语气，避免说教。用中文回答。"""

SYSTEM_PROMPT_TRENDS = """你是一位善于数据分析的人生教练。用户会提供多天的活动记录。

请分析：
1. 【整体趋势】几天来的活动模式有什么变化
2. 【亮点发现】值得肯定的习惯或进步
3. 【改进建议】基于数据给出2-3条具体可行的建议
4. 【一周展望】对下一阶段的活动安排建议

用温暖、鼓励的语气，避免说教。用中文回答。"""


def _get_client():
    if not ANTHROPIC_API_KEY:
        raise ValueError('请设置 ANTHROPIC_API_KEY 环境变量')
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _format_activities(activities):
    lines = []
    for a in activities:
        lines.append(f"[{a['time_start']}-{a['time_end']}] [{a['category']}] {a['content']}")
    return '\n'.join(lines)


def generate_daily_reflection(activities):
    client = _get_client()
    formatted = _format_activities(activities)
    date = activities[0]['date']

    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT_REFLECTION,
        messages=[{
            'role': 'user',
            'content': f'{date} 的活动记录：\n\n{formatted}'
        }]
    )

    text = response.content[0].text

    # Split into summary and reflection
    if '【深度反思】' in text:
        parts = text.split('【深度反思】', 1)
        summary = parts[0].replace('【今日总结】', '').strip()
        reflection = parts[1].strip()
    else:
        summary = text[:200]
        reflection = text

    return {'summary': summary, 'reflection': reflection}


SYSTEM_PROMPT_GUIDE = """你是一位擅长引导式对话的心理教练。用户会告诉你他今天想解决的问题，以及今天的活动记录。

你的任务是通过提问，帮助用户更清晰地回忆和表达与这个问题相关的细节、感受和经历。

规则：
- 每次只问一个问题
- 问开放性问题（不能是「是/否」就能回答的）
- 不给建议、不下判断、不给选项
- 根据用户上一条回答深入追问
- 语气温和、好奇、不评判
- 用中文回答"""

SYSTEM_PROMPT_SOLUTION = """你是一位专业的人生教练，擅长结合心理学知识和用户的实际情况给出建议。

你会收到：
1. 用户想解决的问题
2. 用户今天的活动记录
3. 引导对话的完整内容（用户回忆的细节）
4. 相关的知识库内容
5. 用户过去的历史数据（如有）

请基于以上所有信息，给出：
1. 【问题分析】简要总结你对这个问题的理解（2-3句话）
2. 【核心洞察】从对话中发现的关键模式或根源（1-2条）
3. 【具体行动】3-5条可以立即执行的建议，每条要：
   - 具体（不是模糊的「多运动」，而是「每天饭后散步15分钟」）
   - 有依据（简短说明为什么这样做有效）
4. 【本周小实验】选一个最容易开始的行动，设计成「本周实验」

语气温暖、务实、充满希望。用中文回答。"""


def start_guided_review(activities, user_problem):
    """开始引导回顾，生成第一个引导问题"""
    client = _get_client()
    formatted = _format_activities(activities) if activities else '今天暂无活动记录'

    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT_GUIDE,
        messages=[{
            'role': 'user',
            'content': (
                f'我今天想解决的问题是：{user_problem}\n\n'
                f'今天的活动记录：\n{formatted}\n\n'
                f'请问我第一个引导问题，帮我更深入地思考这个问题。'
            )
        }]
    )
    return response.content[0].text


def continue_guided_review(activities, messages, user_problem):
    """根据对话历史继续引导，生成下一个问题"""
    client = _get_client()
    formatted = _format_activities(activities) if activities else '今天暂无活动记录'

    # 构建对话历史
    conversation = [{
        'role': 'user',
        'content': (
            f'我今天想解决的问题是：{user_problem}\n\n'
            f'今天的活动记录：\n{formatted}\n\n'
            f'请问我第一个引导问题，帮我更深入地思考这个问题。'
        )
    }]

    for msg in messages:
        conversation.append({
            'role': msg['role'],
            'content': msg['content']
        })

    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=300,
        system=SYSTEM_PROMPT_GUIDE,
        messages=conversation
    )
    return response.content[0].text


def generate_solution(activities, messages, user_problem, knowledge_context, history_context):
    """综合所有信息生成最终建议"""
    client = _get_client()
    formatted = _format_activities(activities) if activities else '今天暂无活动记录'

    # 整理对话内容
    conversation_text = '\n'.join([
        f"{'用户' if m['role'] == 'user' else 'AI教练'}：{m['content']}"
        for m in messages
    ])

    # 构建完整上下文
    content_parts = [
        f'## 用户的问题\n{user_problem}',
        f'## 今天的活动记录\n{formatted}',
        f'## 引导对话内容\n{conversation_text}',
    ]

    if knowledge_context:
        content_parts.append(f'## 相关知识参考\n{knowledge_context}')

    if history_context:
        content_parts.append(f'## 用户历史数据\n{history_context}')

    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT_SOLUTION,
        messages=[{
            'role': 'user',
            'content': '\n\n---\n\n'.join(content_parts)
        }]
    )
    return response.content[0].text


def generate_trend_analysis(activities):
    client = _get_client()

    # Group by date
    by_date = {}
    for a in activities:
        by_date.setdefault(a['date'], []).append(a)

    lines = []
    for date in sorted(by_date.keys()):
        lines.append(f'\n--- {date} ---')
        lines.append(_format_activities(by_date[date]))

    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT_TRENDS,
        messages=[{
            'role': 'user',
            'content': f'以下是多天的活动记录：\n{"".join(lines)}'
        }]
    )

    return response.content[0].text
