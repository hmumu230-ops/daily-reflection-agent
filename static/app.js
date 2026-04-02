// ========== localStorage 数据层 ==========
// 所有对话数据以 localStorage 为主存储，服务器只做 AI 计算

const STORAGE_KEY = 'reflection_sessions';

// 统一 fetch 包装：遇到 401 自动跳转登录页
async function apiFetch(url, options) {
    const res = await fetch(url, options);
    if (res.status === 401) {
        window.location.href = '/login';
        throw new Error('未登录');
    }
    return res;
}

function getAllSessions() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    } catch { return {}; }
}

function getSession(date) {
    return getAllSessions()[date] || null;
}

function saveSession(date, data) {
    const all = getAllSessions();
    all[date] = { ...all[date], ...data, updatedAt: new Date().toISOString() };
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
        console.log('[反思] 已保存会话:', date, data.status || 'update');
    } catch (e) {
        console.error('[反思] localStorage 保存失败:', e);
    }
}

function deleteSession(date) {
    const all = getAllSessions();
    delete all[date];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

// ========== Navigation ==========

function changeDate(delta) {
    const input = document.getElementById('current-date');
    const d = new Date(input.value);
    d.setDate(d.getDate() + delta);
    goToDate(d.toISOString().split('T')[0]);
}

function goToDate(date) {
    location.href = '/day/' + date;
}

// ========== Guided Review ==========

let reviewSessionId = null;
let chatHistory = [];
let currentProblem = '';

function loadExistingReview(date) {
    const session = getSession(date);
    if (!session) return;

    if (session.status === 'completed' && session.solution) {
        showResult(session.solution, session.categories || [], session.problem);
        return;
    }

    if (session.history && session.history.length > 0) {
        currentProblem = session.problem;
        chatHistory = session.history;
        reviewSessionId = session.sessionId || null;
        restoreChatUI(session.problem, session.history);
    }
}

function restoreChatUI(problem, messages) {
    document.getElementById('review-start').style.display = 'none';
    document.getElementById('review-chat').style.display = 'block';
    document.getElementById('chat-problem-label').textContent = problem;
    const container = document.getElementById('chat-messages');
    container.innerHTML = '';
    for (const msg of messages) {
        appendBubble(msg.content, msg.role === 'user' ? 'user' : 'ai');
    }
}

async function startReview() {
    const problem = document.getElementById('problem-input').value.trim();
    if (!problem) {
        document.getElementById('problem-input').focus();
        return;
    }

    const btn = document.getElementById('start-btn');
    btn.textContent = '思考中…';
    btn.disabled = true;

    try {
        const res = await apiFetch(`/api/review/${currentDate}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ problem })
        });
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            btn.textContent = '开始对话';
            btn.disabled = false;
            return;
        }

        reviewSessionId = data.session_id;
        currentProblem = problem;
        chatHistory = [{ role: 'assistant', content: data.message }];

        saveSession(currentDate, {
            problem: currentProblem,
            history: chatHistory,
            sessionId: reviewSessionId,
            status: 'in_progress'
        });

        document.getElementById('review-start').style.display = 'none';
        document.getElementById('review-chat').style.display = 'block';
        document.getElementById('chat-problem-label').textContent = problem;

        const container = document.getElementById('chat-messages');
        container.innerHTML = '';
        appendBubble(data.message, 'ai');
    } catch (err) {
        alert('网络错误，请重试');
        btn.textContent = '开始对话';
        btn.disabled = false;
    }
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    appendBubble(message, 'user');

    const thinking = appendBubble('思考中…', 'ai');

    try {
        const res = await apiFetch(`/api/review/${currentDate}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                problem: currentProblem,
                history: chatHistory
            })
        });
        const data = await res.json();

        thinking.remove();

        if (data.error) {
            appendBubble('出错了：' + data.error, 'ai');
            return;
        }

        chatHistory.push({ role: 'user', content: message });
        chatHistory.push({ role: 'assistant', content: data.message });

        saveSession(currentDate, {
            problem: currentProblem,
            history: chatHistory,
            sessionId: reviewSessionId,
            status: 'in_progress'
        });

        appendBubble(data.message, 'ai');
    } catch (err) {
        thinking.remove();
        appendBubble('网络错误，请重试', 'ai');
    }
}

function handleChatKey(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
}

async function finishReview() {
    const btn = document.getElementById('finish-btn');
    btn.textContent = '分析中…';
    btn.disabled = true;

    try {
        const res = await apiFetch(`/api/review/${currentDate}/finish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problem: currentProblem,
                history: chatHistory
            })
        });
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            btn.textContent = '生成建议 →';
            btn.disabled = false;
            return;
        }

        const problem = document.getElementById('chat-problem-label').textContent;

        saveSession(currentDate, {
            problem: currentProblem,
            history: chatHistory,
            solution: data.solution,
            categories: data.categories || [],
            status: 'completed'
        });

        document.getElementById('review-chat').style.display = 'none';
        showResult(data.solution, data.categories || [], problem);
    } catch (err) {
        alert('网络错误，请重试');
        btn.textContent = '生成建议 →';
        btn.disabled = false;
    }
}

function showResult(solution, categories, problem) {
    document.getElementById('review-result').style.display = 'block';
    document.getElementById('review-start').style.display = 'none';
    document.getElementById('review-chat').style.display = 'none';

    document.getElementById('result-problem').textContent = problem || '';

    const tagsEl = document.getElementById('result-tags');
    tagsEl.innerHTML = categories.map(c =>
        `<span class="result-tag">${c}</span>`
    ).join('');

    document.getElementById('solution-content').innerHTML = renderText(solution);
}

function resetReview() {
    reviewSessionId = null;
    chatHistory = [];
    currentProblem = '';
    deleteSession(currentDate);
    document.getElementById('review-result').style.display = 'none';
    document.getElementById('review-start').style.display = 'block';
    document.getElementById('problem-input').value = '';

    const btn = document.getElementById('start-btn');
    if (btn) {
        btn.textContent = '开始对话';
        btn.disabled = false;
    }
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

// ========== 息屏恢复 ==========
// 当用户从息屏/切后台回来时，重新从 localStorage 加载状态

document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && typeof currentDate !== 'undefined') {
        const session = getSession(currentDate);
        if (session && session.history && session.history.length > 0 && chatHistory.length === 0) {
            loadExistingReview(currentDate);
        }
    }
});

// ========== 历史记录页面渲染 ==========

function renderHistoryPage() {
    const container = document.getElementById('history-container');
    if (!container) return;

    const all = getAllSessions();
    const dates = Object.keys(all).sort().reverse();

    if (dates.length === 0) {
        container.innerHTML = `
            <div class="history-empty">
                还没有记录<br>
                <a href="/" style="color: var(--accent); text-decoration: none;">开始今天的第一次对话 →</a>
            </div>`;
        return;
    }

    container.innerHTML = dates.map(date => {
        const s = all[date];
        const statusClass = s.status === 'completed' ? 'completed' : 'in-progress';
        const statusText = s.status === 'completed' ? '已完成' : '进行中';
        return `
            <a href="/day/${date}" class="history-item">
                <div class="history-date">${date}</div>
                <div class="history-problem">${escapeHtml(s.problem || '')}</div>
                <span class="history-status ${statusClass}">${statusText}</span>
            </a>`;
    }).join('');
}

function renderText(str) {
    if (!str) return '';
    // 先转义 HTML，再把换行变 <br>，把 **text** 变粗体
    let html = str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');
    return html;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
