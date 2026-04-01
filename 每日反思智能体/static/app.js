const CATEGORIES = ['身心活动', '意识活动', '精神活动', '行为活动'];
const CAT_COLORS = ['#4a90d9', '#27ae60', '#8e44ad', '#e67e22'];

function catClass(category) {
    const idx = CATEGORIES.indexOf(category) + 1;
    return 'cat-' + (idx || 1);
}

function catIndex(category) {
    return CATEGORIES.indexOf(category);
}

// --- Timeline Page ---

async function loadActivities(date) {
    const res = await fetch('/api/activities?date=' + date);
    const activities = await res.json();
    const timeline = document.getElementById('timeline');
    const emptyState = document.getElementById('empty-state');
    if (!timeline) return;

    if (!activities.length) {
        emptyState.style.display = 'block';
        return;
    }
    emptyState.style.display = 'none';

    let html = '';
    for (const a of activities) {
        html += `
        <div class="activity-card ${catClass(a.category)}">
            <div class="activity-info">
                <div class="activity-time">${a.time_start} - ${a.time_end}</div>
                <span class="activity-category ${catClass(a.category)}">${a.category}</span>
                <div class="activity-content">${escapeHtml(a.content)}</div>
            </div>
            <div class="activity-actions">
                <button onclick="location.href='/record/${a.id}'" title="编辑">&#9998;</button>
                <button onclick="deleteActivity(${a.id})" title="删除">&#10005;</button>
            </div>
        </div>`;
    }
    timeline.innerHTML = html;

    // Load existing reflection
    loadReflection(date);
}

async function loadReflection(date) {
    const res = await fetch('/api/reflect/' + date);
    const ref = await res.json();
    const content = document.getElementById('reflection-content');
    if (!content) return;

    if (ref && ref.summary) {
        content.innerHTML = `
            <div class="reflection-card">
                <h4>今日总结</h4>
                <p>${escapeHtml(ref.summary)}</p>
                <h4 style="margin-top:16px">深度反思</h4>
                <p>${escapeHtml(ref.reflection)}</p>
            </div>
            <button class="btn btn-secondary" style="margin-top:12px" onclick="generateReflection()">重新生成</button>`;
    }
}

async function generateReflection() {
    const date = document.getElementById('current-date').value;
    const content = document.getElementById('reflection-content');
    content.innerHTML = '<div class="loading">AI 正在生成反思</div>';

    const res = await fetch('/api/reflect/' + date, { method: 'POST' });
    const data = await res.json();

    if (data.error) {
        content.innerHTML = `<p style="color:#e74c3c">${escapeHtml(data.error)}</p>
            <button class="btn btn-secondary" onclick="generateReflection()">重试</button>`;
        return;
    }

    content.innerHTML = `
        <div class="reflection-card">
            <h4>今日总结</h4>
            <p>${escapeHtml(data.summary)}</p>
            <h4 style="margin-top:16px">深度反思</h4>
            <p>${escapeHtml(data.reflection)}</p>
        </div>
        <button class="btn btn-secondary" style="margin-top:12px" onclick="generateReflection()">重新生成</button>`;
}

async function deleteActivity(id) {
    if (!confirm('确定删除这条活动记录吗？')) return;
    await fetch('/api/activities/' + id, { method: 'DELETE' });
    location.reload();
}

function changeDate(delta) {
    const input = document.getElementById('current-date');
    const d = new Date(input.value);
    d.setDate(d.getDate() + delta);
    goToDate(d.toISOString().split('T')[0]);
}

function goToDate(date) {
    location.href = '/day/' + date;
}

// --- Record Form ---

async function submitActivity(e) {
    e.preventDefault();
    const id = document.getElementById('activity-id').value;
    const data = {
        date: document.getElementById('f-date').value,
        time_start: document.getElementById('f-start').value,
        time_end: document.getElementById('f-end').value,
        category: document.querySelector('input[name="category"]:checked').value,
        content: document.getElementById('f-content').value
    };

    const url = id ? '/api/activities/' + id : '/api/activities';
    const method = id ? 'PUT' : 'POST';

    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    const result = await res.json();

    if (result.error) {
        alert(result.error);
        return false;
    }
    location.href = '/day/' + data.date;
    return false;
}

// --- Analysis Page ---

function initAnalysis() {
    const dateFrom = document.getElementById('date-from');
    const dateTo = document.getElementById('date-to');
    if (!dateFrom || !dateTo) return;

    const today = new Date();
    const weekAgo = new Date();
    weekAgo.setDate(today.getDate() - 6);
    dateTo.value = today.toISOString().split('T')[0];
    dateFrom.value = weekAgo.toISOString().split('T')[0];
}

async function loadAnalysis() {
    const dateFrom = document.getElementById('date-from').value;
    const dateTo = document.getElementById('date-to').value;
    const res = await fetch(`/api/activities?from=${dateFrom}&to=${dateTo}`);
    const activities = await res.json();

    if (!activities.length) {
        document.getElementById('stats-section').style.display = 'none';
        document.getElementById('trend-section').style.display = 'none';
        alert('所选时间段没有活动记录');
        return;
    }

    document.getElementById('stats-section').style.display = 'block';
    document.getElementById('trend-section').style.display = 'block';

    renderStats(activities);
    renderChart(activities, dateFrom, dateTo);
}

function renderStats(activities) {
    const grid = document.getElementById('stats-grid');
    const hours = [0, 0, 0, 0];

    for (const a of activities) {
        const idx = catIndex(a.category);
        if (idx < 0) continue;
        const start = timeToMinutes(a.time_start);
        const end = timeToMinutes(a.time_end);
        if (end > start) hours[idx] += (end - start) / 60;
    }

    grid.innerHTML = CATEGORIES.map((cat, i) => `
        <div class="stat-card cat-${i + 1}">
            <div class="stat-value">${hours[i].toFixed(1)}h</div>
            <div class="stat-label">${cat}</div>
        </div>
    `).join('');
}

function renderChart(activities, dateFrom, dateTo) {
    const container = document.getElementById('chart-container');
    const dayMap = {};

    // Group by date
    for (const a of activities) {
        if (!dayMap[a.date]) dayMap[a.date] = [0, 0, 0, 0];
        const idx = catIndex(a.category);
        if (idx < 0) continue;
        const start = timeToMinutes(a.time_start);
        const end = timeToMinutes(a.time_end);
        if (end > start) dayMap[a.date][idx] += (end - start) / 60;
    }

    const dates = Object.keys(dayMap).sort();
    const maxHours = Math.max(...dates.map(d => dayMap[d].reduce((a, b) => a + b, 0)), 1);

    container.innerHTML = dates.map(d => {
        const total = dayMap[d].reduce((a, b) => a + b, 0);
        const segments = dayMap[d].map((h, i) =>
            h > 0 ? `<div class="chart-segment" style="width:${(h / maxHours) * 100}%;background:${CAT_COLORS[i]}"></div>` : ''
        ).join('');
        return `
        <div class="chart-row">
            <span class="chart-label">${d.slice(5)}</span>
            <div class="chart-bar-group">${segments}</div>
            <span class="chart-label" style="text-align:right;width:50px">${total.toFixed(1)}h</span>
        </div>`;
    }).join('');
}

async function generateTrends() {
    const dateFrom = document.getElementById('date-from').value;
    const dateTo = document.getElementById('date-to').value;
    const d1 = new Date(dateFrom);
    const d2 = new Date(dateTo);
    const days = Math.round((d2 - d1) / (1000 * 60 * 60 * 24)) + 1;

    const content = document.getElementById('trend-content');
    content.innerHTML = '<div class="loading">AI 正在分析趋势</div>';

    const res = await fetch('/api/trends?days=' + days);
    const data = await res.json();

    if (data.error) {
        content.innerHTML = `<p style="color:#e74c3c">${escapeHtml(data.error)}</p>
            <button class="btn btn-secondary" onclick="generateTrends()">重试</button>`;
        return;
    }

    content.innerHTML = `<div class="trend-text">${escapeHtml(data.analysis)}</div>
        <button class="btn btn-secondary" style="margin-top:12px" onclick="generateTrends()">重新生成</button>`;
}

// --- Utilities ---

function timeToMinutes(t) {
    const [h, m] = t.split(':').map(Number);
    return h * 60 + m;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;').replace(/\n/g, '<br>');
}

// Auto-init analysis page
document.addEventListener('DOMContentLoaded', initAnalysis);

// --- Guided Review ---

let reviewSessionId = null;

async function loadExistingReview(date) {
    const res = await fetch('/api/review/' + date);
    const session = await res.json();
    if (!session) return;

    if (session.status === 'completed') {
        // 已完成：显示最后一条 AI 建议（从反思中读取）
        const ref = await fetch('/api/reflect/' + date).then(r => r.json());
        if (ref && ref.reflection) {
            showResult(ref.reflection, []);
        }
    } else if (session.messages && session.messages.length > 0) {
        // 进行中：恢复对话
        reviewSessionId = session.id;
        document.getElementById('review-start').style.display = 'none';
        document.getElementById('review-chat').style.display = 'block';
        document.getElementById('chat-problem-label').textContent = session.user_problem;
        const container = document.getElementById('chat-messages');
        container.innerHTML = '';
        for (const msg of session.messages) {
            appendBubble(msg.content, msg.role === 'user' ? 'user' : 'ai');
        }
    }
}

async function startReview() {
    const problem = document.getElementById('problem-input').value.trim();
    if (!problem) {
        alert('请先描述你想解决的问题');
        return;
    }

    const btn = document.querySelector('#review-start .btn-primary');
    btn.textContent = 'AI 思考中…';
    btn.disabled = true;

    const res = await fetch(`/api/review/${currentDate}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem })
    });
    const data = await res.json();

    if (data.error) {
        alert(data.error);
        btn.textContent = '开始回顾';
        btn.disabled = false;
        return;
    }

    reviewSessionId = data.session_id;
    document.getElementById('review-start').style.display = 'none';
    document.getElementById('review-chat').style.display = 'block';
    document.getElementById('chat-problem-label').textContent = problem;

    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    appendBubble(data.message, 'ai');
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    appendBubble(message, 'user');

    const thinking = appendBubble('思考中…', 'ai');

    const res = await fetch(`/api/review/${currentDate}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    });
    const data = await res.json();

    thinking.remove();

    if (data.error) {
        appendBubble('出错了：' + data.error, 'ai');
        return;
    }
    appendBubble(data.message, 'ai');
}

function handleChatKey(e) {
    // Ctrl/Cmd + Enter 发送
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
}

async function finishReview() {
    const btn = document.querySelector('#review-chat .btn-primary');
    btn.textContent = 'AI 分析中…';
    btn.disabled = true;

    const res = await fetch(`/api/review/${currentDate}/finish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();

    btn.textContent = '生成建议 →';
    btn.disabled = false;

    if (data.error) {
        alert(data.error);
        return;
    }

    document.getElementById('review-chat').style.display = 'none';
    showResult(data.solution, data.categories || []);
}

function showResult(solution, categories) {
    document.getElementById('review-result').style.display = 'block';
    document.getElementById('review-start').style.display = 'none';
    document.getElementById('review-chat').style.display = 'none';

    const catEl = document.getElementById('result-categories');
    catEl.innerHTML = categories.map(c =>
        `<span class="result-category-tag">${c}</span>`
    ).join('');

    document.getElementById('solution-content').textContent = solution;
}

function resetReview() {
    reviewSessionId = null;
    document.getElementById('review-result').style.display = 'none';
    document.getElementById('review-start').style.display = 'block';
    document.getElementById('problem-input').value = '';
}

function appendBubble(text, type) {
    const container = document.getElementById('chat-messages');
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${type}`;
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
    return bubble;
}
