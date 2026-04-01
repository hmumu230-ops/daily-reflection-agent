// --- Navigation ---

function changeDate(delta) {
    const input = document.getElementById('current-date');
    const d = new Date(input.value);
    d.setDate(d.getDate() + delta);
    goToDate(d.toISOString().split('T')[0]);
}

function goToDate(date) {
    location.href = '/day/' + date;
}

// --- Guided Review ---

let reviewSessionId = null;

async function loadExistingReview(date) {
    const res = await fetch('/api/review/' + date);
    const session = await res.json();
    if (!session) return;

    if (session.status === 'completed') {
        // 已完成：展示结果
        const ref = await fetch('/api/reflect/' + date).then(r => r.json());
        if (ref && ref.reflection) {
            showResult(ref.reflection, [], session.user_problem);
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
        document.getElementById('problem-input').focus();
        return;
    }

    const btn = document.getElementById('start-btn');
    btn.textContent = '思考中…';
    btn.disabled = true;

    try {
        const res = await fetch(`/api/review/${currentDate}/start`, {
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
        const res = await fetch(`/api/review/${currentDate}/finish`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            btn.textContent = '生成建议 →';
            btn.disabled = false;
            return;
        }

        const problem = document.getElementById('chat-problem-label').textContent;
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

    document.getElementById('solution-content').textContent = solution;
}

function resetReview() {
    reviewSessionId = null;
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

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;').replace(/\n/g, '<br>');
}
