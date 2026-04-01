from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import date, timedelta
from models import (
    init_db, insert_activity, get_activities_by_date, get_activities_by_range,
    get_activity_by_id, update_activity, delete_activity,
    save_reflection, get_reflection
)
from config import SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY

CATEGORIES = ['身心活动', '意识活动', '精神活动', '行为活动']


# --- Page Routes ---

@app.route('/')
def index():
    today = date.today().isoformat()
    return render_template('index.html', date=today, categories=CATEGORIES)


@app.route('/day/<day>')
def day_view(day):
    return render_template('index.html', date=day, categories=CATEGORIES)


@app.route('/record')
def record_new():
    today = date.today().isoformat()
    return render_template('record.html', activity=None, date=today, categories=CATEGORIES)


@app.route('/record/<int:activity_id>')
def record_edit(activity_id):
    activity = get_activity_by_id(activity_id)
    if not activity:
        return redirect(url_for('index'))
    return render_template('record.html', activity=activity, date=activity['date'], categories=CATEGORIES)


@app.route('/analysis')
def analysis():
    return render_template('analysis.html')


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


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
