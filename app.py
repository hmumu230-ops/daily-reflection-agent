from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import date, timedelta
from models import (
    init_db, insert_activity, get_activities_by_date, get_activities_by_range,
    get_activity_by_id, update_activity, delete_activity,
    save_reflection, get_reflection,
    create_review_session, add_review_message, get_review_session, complete_review_session,
    get_all_review_sessions
)
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

CATEGORIES = ['身心活动', '意识活动', '精神活动', '行为活动']


# --- Page Routes ---

@app.route('/')
def index():
    today = date.today().isoformat()
    return render_template('index.html', date=today)


@app.route('/day/<day>')
def day_view(day):
    return render_template('index.html', date=day)


@app.route('/history')
def history():
    sessions = get_all_review_sessions()
    return render_template('history.html', sessions=sessions)


# --- API Routes ---

@app.route('/api/activities', methods=['GET'])
def api_get_activities():
    d = request.args.get('date', date.today().isoformat())
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    if date_from and date_to:
        activities = get_activities_by_range(date_from, date_to)
    else:
        activities = get_activities_by_date(d)
    return jsonify(activities)


@app.route('/api/activities', methods=['POST'])
def api_create_activity():
    data = request.get_json()
    required = ['date', 'time_start', 'time_end', 'category', 'content']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'缺少字段: {field}'}), 400
    if data['category'] not in CATEGORIES:
        return jsonify({'error': '无效的活动类别'}), 400
    activity_id = insert_activity(
        data['date'], data['time_start'], data['time_end'],
        data['category'], data['content']
    )
    return jsonify({'id': activity_id}), 201


@app.route('/api/activities/<int:activity_id>', methods=['PUT'])
def api_update_activity(activity_id):
    data = request.get_json()
    existing = get_activity_by_id(activity_id)
    if not existing:
        return jsonify({'error': '活动不存在'}), 404
    update_activity(
        activity_id,
        data.get('date', existing['date']),
        data.get('time_start', existing['time_start']),
        data.get('time_end', existing['time_end']),
        data.get('category', existing['category']),
        data.get('content', existing['content'])
    )
    return jsonify({'ok': True})


@app.route('/api/activities/<int:activity_id>', methods=['DELETE'])
def api_delete_activity(activity_id):
    delete_activity(activity_id)
    return jsonify({'ok': True})


@app.route('/api/reflect/<day>', methods=['GET'])
def api_get_reflection(day):
    ref = get_reflection(day)
    if ref:
        return jsonify(ref)
    return jsonify(None)


@app.route('/api/reflect/<day>', methods=['POST'])
def api_generate_reflection(day):
    activities = get_activities_by_date(day)
    if not activities:
        return jsonify({'error': '当天没有活动记录，无法生成反思'}), 400
    try:
        from ai_service import generate_daily_reflection
        result = generate_daily_reflection(activities)
        save_reflection(day, result['summary'], result['reflection'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/review/<day>/start', methods=['POST'])
def api_review_start(day):
    """开始引导回顾：用户说出问题，AI 给出第一个引导问题"""
    data = request.get_json()
    user_problem = data.get('problem', '').strip()
    if not user_problem:
        return jsonify({'error': '请先描述你想解决的问题'}), 400

    activities = get_activities_by_date(day)
    session_id = create_review_session(day, user_problem)

    try:
        from ai_service import start_guided_review
        ai_question = start_guided_review(activities, user_problem)
        add_review_message(session_id, 'assistant', ai_question)
        return jsonify({'session_id': session_id, 'message': ai_question})
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/review/<day>/message', methods=['POST'])
def api_review_message(day):
    """用户发送消息，AI 继续引导追问"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': '消息不能为空'}), 400

    session = get_review_session(day)
    if not session:
        return jsonify({'error': '请先开始回顾会话'}), 404
    if session['status'] == 'completed':
        return jsonify({'error': '本次回顾已结束'}), 400

    add_review_message(session['id'], 'user', user_message)

    activities = get_activities_by_date(day)
    messages = session['messages'] + [{'role': 'user', 'content': user_message}]

    try:
        from ai_service import continue_guided_review
        ai_reply = continue_guided_review(activities, messages, session['user_problem'])
        add_review_message(session['id'], 'assistant', ai_reply)
        return jsonify({'message': ai_reply})
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/review/<day>/finish', methods=['POST'])
def api_review_finish(day):
    """结束回顾，使用 RAG 生成最终建议"""
    session = get_review_session(day)
    if not session:
        return jsonify({'error': '请先开始回顾会话'}), 404

    complete_review_session(session['id'])

    activities = get_activities_by_date(day)

    try:
        from ai_service import generate_solution
        from rag_service import build_rag_context
        from models import get_db

        conn = get_db()
        rag = build_rag_context(session['user_problem'], day, conn)
        conn.close()

        solution = generate_solution(
            activities=activities,
            messages=session['messages'],
            user_problem=session['user_problem'],
            knowledge_context=rag['knowledge'],
            history_context=rag['history']
        )
        save_reflection(day, f"回顾问题：{session['user_problem']}", solution)
        return jsonify({
            'solution': solution,
            'categories': rag['categories']
        })
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/review/<day>', methods=['GET'])
def api_review_get(day):
    """获取当天的回顾会话（如果存在）"""
    session = get_review_session(day)
    if not session:
        return jsonify(None)
    return jsonify(session)


@app.route('/api/trends', methods=['GET'])
def api_trends():
    days = int(request.args.get('days', 7))
    end = date.today()
    start = end - timedelta(days=days - 1)
    activities = get_activities_by_range(start.isoformat(), end.isoformat())
    if not activities:
        return jsonify({'error': '所选时间段没有活动记录'}), 400
    try:
        from ai_service import generate_trend_analysis
        result = generate_trend_analysis(activities)
        return jsonify({'analysis': result})
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
