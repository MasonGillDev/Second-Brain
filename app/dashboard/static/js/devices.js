/* Devices — folder-watcher clients (read-only status). */
(function() {
    const tbody = document.getElementById('dev-tbody');
    let pollTimer = null;

    window.addEventListener('tab:devices', () => { load(); startPolling(); });
    document.getElementById('dev-refresh-btn').addEventListener('click', load);

    // Stop polling when another tab is active (only poll while Devices is shown).
    document.querySelectorAll('.nav-btn[data-tab]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.tab !== 'devices') stopPolling();
        });
    });

    function startPolling() {
        stopPolling();
        pollTimer = setInterval(load, 15000);
    }
    function stopPolling() {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    }

    function ago(ts) {
        const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
        if (s < 60) return s + 's ago';
        if (s < 3600) return Math.floor(s / 60) + 'm ago';
        if (s < 86400) return Math.floor(s / 3600) + 'h ago';
        return Math.floor(s / 86400) + 'd ago';
    }

    async function load() {
        const data = await api('/api/devices');
        if (!data) return;
        document.getElementById('dev-empty').style.display = data.length ? 'none' : '';
        tbody.innerHTML = data.map(d => {
            const dot = d.online ? 'green' : 'text-dim';
            const status = d.online ? 'online' : ago(d.last_seen);
            const paths = (d.watch_paths || []);
            const pathsHtml = paths.length
                ? paths.map(p => `<div style="font-size:11px;color:var(--text-dim);font-family:monospace">${esc(p)}</div>`).join('')
                : '<span style="color:var(--text-dim)">—</span>';
            return `<tr>
                <td><span class="status-dot" style="background:var(--${dot});display:inline-block"></span>
                    <span style="font-weight:500">${esc(d.hostname || d.device_id)}</span></td>
                <td style="font-size:12px">${esc(d.platform || '')}</td>
                <td style="max-width:340px">${pathsHtml}</td>
                <td style="font-size:12px">${d.files_sent}</td>
                <td style="font-size:11px;color:var(--text-dim);white-space:nowrap">${status}</td>
            </tr>`;
        }).join('');
    }

    function esc(s) {
        const el = document.createElement('div');
        el.textContent = s == null ? '' : s;
        return el.innerHTML;
    }
})();
