/* Sleep agent controls */
(function() {
    const runBtn = document.getElementById('sleep-run');
    const dryRunCheck = document.getElementById('sleep-dry-run');
    const statusDot = document.getElementById('sleep-status-dot');
    const statusLabel = document.getElementById('sleep-status-label');
    const logList = document.getElementById('sleep-log-list');
    const logViewer = document.getElementById('sleep-log-viewer');

    runBtn.addEventListener('click', async () => {
        runBtn.disabled = true;
        const data = await api('/api/sleep/run', {
            method: 'POST',
            body: JSON.stringify({ dry_run: dryRunCheck.checked }),
        });
        if (data && data.status === 'started') {
            setStatus(true);
            pollStatus();
        } else {
            runBtn.disabled = false;
        }
    });

    function setStatus(running) {
        statusDot.className = running ? 'status-dot working' : 'status-dot';
        statusLabel.textContent = running ? 'Running...' : 'Idle';
        runBtn.disabled = running;
    }

    async function pollStatus() {
        const data = await api('/api/sleep/status');
        if (data && data.running) {
            setTimeout(pollStatus, 2000);
        } else {
            setStatus(false);
            loadLogs();
        }
    }

    async function loadLogs() {
        const data = await api('/api/sleep/logs');
        if (!data) return;
        logList.innerHTML = data.logs.map(f =>
            `<button class="log-file-btn" data-file="${f}">${f}</button>`
        ).join('');
    }

    logList.addEventListener('click', async (e) => {
        const btn = e.target.closest('.log-file-btn');
        if (!btn) return;
        logList.querySelectorAll('.log-file-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const data = await api(`/api/sleep/logs/${btn.dataset.file}`);
        if (data) logViewer.textContent = data.content;
    });

    window.addEventListener('tab:sleep', () => {
        loadLogs();
        api('/api/sleep/status').then(d => { if (d) setStatus(d.running); });
    });
})();
