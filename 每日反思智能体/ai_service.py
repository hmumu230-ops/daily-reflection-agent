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
