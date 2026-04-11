from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from models import (
    init_db, get_user_by_username, get_user_by_id, create_user,
    insert_activity, get_activities_by_date, get_activities_by_range,
    get_activity_by_id, update_activity, delete_activity,
    save_reflection, get_reflection,
    create_review_session, add_review_message, get_review_session, complete_review_session,
    get_all_review_sessions,
    save_note_summary, get_note_summary, get_note_summaries_by_range
)
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

import time
BOOT_TIME = str(int(time.time()))


@app.after_request
def add_no_cache(response):
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
    return response


@app.context_processor
def inject_cache_bust():
    return {'cache_bust': BOOT_TIME}

# --- Flask-Login ---

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    row = get_user_by_id(int(user_id))
    if row:
        return User(row['id'], row['username'])
    return None


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith('/api/'):
        return jsonify({'error': '请先登录'}), 401
    return redirect(url_for('login'))


# --- Auth Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = '请填写用户名和密码'
        else:
            user = get_user_by_username(username)
            if user and check_password_hash(user['password_hash'], password):
                login_user(User(user['id'], user['username']), remember=True)
                return redirect(request.args.get('next') or url_for('index'))
            else:
                error = '用户名或密码错误'

    return render_template('login.html', error=error, mode='login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not username or not password:
            error = '请填写用户名和密码'
        elif len(username) < 2 or len(username) > 20:
            error = '用户名需要 2-20 个字符'
        elif len(password) < 6:
            error = '密码至少 6 位'
        elif password != confirm:
            error = '两次密码不一致'
        elif get_user_by_username(username):
            error = '用户名已被注册'
        else:
            user_id = create_user(username, generate_password_hash(password))
            login_user(User(user_id, username), remember=True)
            return redirect(url_for('index'))

    return render_template('login.html', error=error, mode='register')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


# --- Page Routes ---

@app.route('/')
@login_required
def index():
    today = date.today().isoformat()
    return render_template('index.html', date=today)


@app.route('/day/<day>')
@login_required
def day_view(day):
    return render_template('index.html', date=day)


@app.route('/history')
@login_required
def history():
    sessions = get_all_review_sessions(current_user.id)
    return render_template('history.html', sessions=sessions)


@app.route('/weekly')
@login_required
def weekly():
    return render_template('weekly.html')


@app.route('/api/weekly-summary', methods=['POST'])
@login_required
def api_weekly_summary():
    """接收前端传来的本周会话数据，生成周报"""
    data = request.get_json()
    sessions_data = data.get('sessions', [])

    if not sessions_data:
        return jsonify({'error': '本周还没有对话记录，先去聊聊吧'}), 400

    try:
        from ai_service import generate_weekly_summary
        from rag_service import retrieve_knowledge, retrieve_history
        from notes_service import fetch_notes_for_week

        # 从所有会话的问题中提取关键词，匹配知识库
        all_problems = ' '.join([s.get('problem', '') for s in sessions_data])
        knowledge = retrieve_knowledge(all_problems)
        hist = retrieve_history(current_user.id, date.today().isoformat())

        # 获取本周笔记
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        notes_by_date = fetch_notes_for_week(week_start, today.isoformat())

        summary = generate_weekly_summary(sessions_data, knowledge, hist, notes_by_date)
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


# --- API Routes ---

@app.route('/api/activities', methods=['GET'])
@login_required
def api_get_activities():
    d = request.args.get('date', date.today().isoformat())
    date_from = request.args.get('from')
    date_to = request.args.get('to')
    if date_from and date_to:
        activities = get_activities_by_range(current_user.id, date_from, date_to)
    else:
        activities = get_activities_by_date(current_user.id, d)
    return jsonify(activities)


@app.route('/api/activities', methods=['POST'])
@login_required
def api_create_activity():
    data = request.get_json()
    required = ['date', 'time_start', 'time_end', 'category', 'content']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'缺少字段: {field}'}), 400
    activity_id = insert_activity(
        current_user.id, data['date'], data['time_start'], data['time_end'],
        data['category'], data['content']
    )
    return jsonify({'id': activity_id}), 201


@app.route('/api/activities/<int:activity_id>', methods=['PUT'])
@login_required
def api_update_activity(activity_id):
    data = request.get_json()
    existing = get_activity_by_id(current_user.id, activity_id)
    if not existing:
        return jsonify({'error': '活动不存在'}), 404
    update_activity(
        current_user.id, activity_id,
        data.get('date', existing['date']),
        data.get('time_start', existing['time_start']),
        data.get('time_end', existing['time_end']),
        data.get('category', existing['category']),
        data.get('content', existing['content'])
    )
    return jsonify({'ok': True})


@app.route('/api/activities/<int:activity_id>', methods=['DELETE'])
@login_required
def api_delete_activity(activity_id):
    delete_activity(current_user.id, activity_id)
    return jsonify({'ok': True})


@app.route('/api/reflect/<day>', methods=['GET'])
@login_required
def api_get_reflection(day):
    ref = get_reflection(current_user.id, day)
    if ref:
        return jsonify(ref)
    return jsonify(None)


@app.route('/api/reflect/<day>', methods=['POST'])
@login_required
def api_generate_reflection(day):
    activities = get_activities_by_date(current_user.id, day)
    if not activities:
        return jsonify({'error': '当天没有活动记录，无法生成反思'}), 400
    try:
        from ai_service import generate_daily_reflection
        result = generate_daily_reflection(activities)
        save_reflection(current_user.id, day, result['summary'], result['reflection'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/review/<day>/start', methods=['POST'])
@login_required
def api_review_start(day):
    data = request.get_json()
    user_problem = data.get('problem', '').strip()
    if not user_problem:
        return jsonify({'error': '请先描述你想解决的问题'}), 400

    activities = get_activities_by_date(current_user.id, day)
    session_id = create_review_session(current_user.id, day, user_problem)

    try:
        from ai_service import start_guided_review
        ai_question = start_guided_review(activities, user_problem)
        add_review_message(session_id, 'assistant', ai_question)
        return jsonify({'session_id': session_id, 'message': ai_question})
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/review/<day>/message', methods=['POST'])
@login_required
def api_review_message(day):
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': '消息不能为空'}), 400

    session = get_review_session(current_user.id, day)

    if not session:
        history = data.get('history', [])
        problem = data.get('problem', '')
        if problem and history:
            session_id = create_review_session(current_user.id, day, problem)
            for msg in history:
                add_review_message(session_id, msg['role'], msg['content'])
            session = get_review_session(current_user.id, day)
        if not session:
            return jsonify({'error': '会话已过期，请刷新页面重新开始'}), 404

    if session['status'] == 'completed':
        return jsonify({'error': '本次回顾已结束'}), 400

    add_review_message(session['id'], 'user', user_message)

    activities = get_activities_by_date(current_user.id, day)
    messages = session['messages'] + [{'role': 'user', 'content': user_message}]

    try:
        from ai_service import continue_guided_review
        ai_reply = continue_guided_review(activities, messages, session['user_problem'])
        add_review_message(session['id'], 'assistant', ai_reply)
        return jsonify({'message': ai_reply})
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/review/<day>/finish', methods=['POST'])
@login_required
def api_review_finish(day):
    data = request.get_json() or {}
    session = get_review_session(current_user.id, day)

    if not session:
        history = data.get('history', [])
        problem = data.get('problem', '')
        if problem and history:
            session_id = create_review_session(current_user.id, day, problem)
            for msg in history:
                add_review_message(session_id, msg['role'], msg['content'])
            session = get_review_session(current_user.id, day)
        if not session:
            return jsonify({'error': '会话已过期，请刷新页面重新开始'}), 404

    complete_review_session(session['id'])

    activities = get_activities_by_date(current_user.id, day)

    try:
        from ai_service import generate_solution
        from rag_service import build_rag_context

        rag = build_rag_context(current_user.id, session['user_problem'], day)

        solution = generate_solution(
            activities=activities,
            messages=session['messages'],
            user_problem=session['user_problem'],
            knowledge_context=rag['knowledge'],
            history_context=rag['history']
        )
        save_reflection(current_user.id, day, f"回顾问题：{session['user_problem']}", solution)
        return jsonify({
            'solution': solution,
            'categories': rag['categories']
        })
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/review/<day>', methods=['GET'])
@login_required
def api_review_get(day):
    session = get_review_session(current_user.id, day)
    if not session:
        return jsonify(None)
    return jsonify(session)


@app.route('/notes')
@login_required
def notes():
    today = date.today().isoformat()
    return render_template('notes.html', date=today)


@app.route('/api/notes/<day>', methods=['GET'])
@login_required
def api_get_notes(day):
    """获取某天的笔记原文列表"""
    from notes_service import fetch_notes_for_date
    notes_list = fetch_notes_for_date(day)
    summary = get_note_summary(current_user.id, day)
    return jsonify({
        'notes': notes_list,
        'summary': summary['summary'] if summary else None
    })


@app.route('/api/notes/<day>/summarize', methods=['POST'])
@login_required
def api_summarize_notes(day):
    """AI 提炼当天笔记"""
    from notes_service import fetch_notes_for_date
    notes_list = fetch_notes_for_date(day)
    if not notes_list:
        return jsonify({'error': f'{day} 没有找到笔记文件'}), 404
    try:
        from ai_service import generate_note_summary
        summary = generate_note_summary(notes_list)
        save_note_summary(current_user.id, day, summary)
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': f'AI 服务出错: {str(e)}'}), 500


@app.route('/api/debug/token-status')
@login_required
def api_debug_token_status():
    """临时诊断端点：检查 GITHUB_TOKEN 状态（不暴露值）"""
    from config import GITHUB_TOKEN, GITHUB_REPO
    import requests as _req
    token = GITHUB_TOKEN or ''
    status = {
        'token_length': len(token),
        'token_stripped_length': len(token.strip()),
        'token_is_ascii': token.isascii() if token else False,
        'token_prefix': token[:4] if token else '',
        'repo': GITHUB_REPO,
    }
    # 实际调用一次 GitHub API 看看结果
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token.strip():
        headers['Authorization'] = f'token {token.strip()}'
    try:
        r = _req.get(f'https://api.github.com/repos/{GITHUB_REPO}/contents/notes', headers=headers, timeout=10)
        status['github_api_status'] = r.status_code
        status['github_api_body'] = r.text[:300]
        status['rate_limit_remaining'] = r.headers.get('x-ratelimit-remaining')
    except Exception as e:
        status['github_api_error'] = str(e)
    return jsonify(status)


@app.route('/api/notes/dates', methods=['GET'])
@login_required
def api_notes_dates():
    """获取有笔记摘要的日期列表"""
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    if not date_from or not date_to:
        today = date.today()
        date_to = today.isoformat()
        date_from = (today - timedelta(days=30)).isoformat()
    summaries = get_note_summaries_by_range(current_user.id, date_from, date_to)
    return jsonify(summaries)


@app.route('/api/trends', methods=['GET'])
@login_required
def api_trends():
    days = int(request.args.get('days', 7))
    end = date.today()
    start = end - timedelta(days=days - 1)
    activities = get_activities_by_range(current_user.id, start.isoformat(), end.isoformat())
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
