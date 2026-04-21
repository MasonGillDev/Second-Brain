/* Live activity log stream (polling) */
(function() {
    const stream = document.getElementById('log-stream');
    const autoScroll = document.getElementById('logs-autoscroll');
    let nextIdx = 0;
    let polling = false;

    function colorize(text) {
        if (text.includes('[tool]')) return 'log-line-tool';
        if (text.includes('[memory]') || text.includes('[extract]')) return 'log-line-memory';
        if (text.includes('[sleep]') || text.includes('[consolidate]')) return 'log-line-sleep';
        if (text.includes('[error]') || text.includes('Error') || text.includes('failed')) return 'log-line-error';
        if (text.includes('[tokens]')) return 'log-line-tokens';
        return '';
    }

    function appendLog(entry) {
        const line = document.createElement('span');
        line.className = colorize(entry.text);
        const ts = new Date(entry.ts * 1000).toLocaleTimeString();
        line.textContent = `[${ts}] ${entry.text}\n`;
        stream.appendChild(line);
        if (autoScroll.checked) {
            stream.scrollTop = stream.scrollHeight;
        }
    }

    async function poll() {
        if (!polling) return;
        try {
            const data = await api(`/api/logs?since=${nextIdx}`);
            if (data && data.entries) {
                data.entries.forEach(appendLog);
                nextIdx = data.next;
            }
        } catch (e) {}
        if (polling) setTimeout(poll, 500);
    }

    function startPolling() {
        if (polling) return;
        polling = true;
        poll();
    }

    function stopPolling() {
        polling = false;
    }

    // Poll when logs tab is active
    window.addEventListener('tab:logs', startPolling);

    // Stop polling when switching away
    document.querySelectorAll('.nav-btn[data-tab]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.tab !== 'logs') stopPolling();
        });
    });

    document.getElementById('logs-clear').addEventListener('click', () => {
        stream.innerHTML = '';
    });
})();
