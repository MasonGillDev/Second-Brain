/* Tab navigation */
document.querySelectorAll('.nav-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const panel = document.getElementById('tab-' + btn.dataset.tab);
        if (panel) panel.classList.add('active');

        // Trigger lazy load
        const event = new CustomEvent('tab:' + btn.dataset.tab);
        window.dispatchEvent(event);
    });
});

/* Utility: fetch JSON with error handling */
window.api = async function(url, opts = {}) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json', ...opts.headers },
        ...opts,
    });
    if (res.status === 401) {
        window.location.href = '/login';
        return null;
    }
    return res.json();
};

/* Utility: websocket with auto-reconnect */
window.createWS = function(path, onMessage, onOpen, onClose) {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    let ws;

    function connect() {
        ws = new WebSocket(proto + '//' + location.host + path);
        ws.onopen = () => { if (onOpen) onOpen(ws); };
        ws.onclose = () => {
            if (onClose) onClose();
            setTimeout(connect, 3000);
        };
        ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                onMessage(data, ws);
            } catch {}
        };
    }

    connect();
    return { send: (d) => ws && ws.readyState === 1 && ws.send(JSON.stringify(d)), get ws() { return ws; } };
};
