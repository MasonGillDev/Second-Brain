/* Triggers — event-driven automations (list + firing log; authoring is agent-via-chat) */
(function() {
    const tbody = document.getElementById('trg-tbody');
    const logTbody = document.getElementById('trg-log-tbody');

    window.addEventListener('tab:triggers', loadAll);
    document.getElementById('trg-refresh-btn').addEventListener('click', loadAll);

    async function loadAll() {
        loadTriggers();
        loadFirings();
    }

    async function loadTriggers() {
        const data = await api('/api/triggers');
        if (!data) return;
        document.getElementById('trg-empty').style.display = data.length ? 'none' : '';
        tbody.innerHTML = data.map(t => {
            const statusCls = t.enabled ? 'green' : 'red';
            const last = t.last_fired ? new Date(t.last_fired * 1000).toLocaleString() : 'Never';
            const srcBadge = t.source_type === 'webhook' ? '&#9889; webhook' : '&#8634; poll';
            return `<tr>
                <td><span class="status-dot" style="background:var(--${statusCls});display:inline-block"></span>
                    <span style="font-weight:500">${esc(t.name)}</span>
                    <div style="font-size:11px;color:var(--text-dim)">${esc(t.description)}</div></td>
                <td><code style="font-size:11px">${srcBadge}</code></td>
                <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px">${esc(t.action)}</td>
                <td style="font-size:12px">${t.sinks.map(esc).join(', ')}</td>
                <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><code style="font-size:11px">${esc(t.filter)}</code></td>
                <td style="font-size:11px;color:var(--text-dim)">${last}</td>
                <td>
                    <button class="action-btn" onclick="trgToggle('${t.name}')">${t.enabled ? 'Disable' : 'Enable'}</button>
                    <button class="action-btn" onclick="trgTest('${t.name}')">Test</button>
                    <button class="action-btn delete" onclick="trgDelete('${t.name}')">Del</button>
                </td>
            </tr>`;
        }).join('');
    }

    async function loadFirings() {
        const rows = await api('/api/triggers/firings?limit=50');
        if (!rows) return;
        document.getElementById('trg-log-empty').style.display = rows.length ? 'none' : '';
        const colors = { fired: 'green', error: 'red', filtered: 'text-dim', debounced: 'yellow' };
        logTbody.innerHTML = rows.map(r => {
            const c = colors[r.status] || 'text-dim';
            const result = (r.result || '').slice(0, 160);
            const dur = r.duration_ms != null ? (r.duration_ms / 1000).toFixed(1) + 's' : '';
            return `<tr>
                <td style="font-size:11px;color:var(--text-dim);white-space:nowrap">${new Date(r.timestamp * 1000).toLocaleString()}</td>
                <td style="font-weight:500">${esc(r.trigger_name)}</td>
                <td style="font-size:12px">${esc(r.source)}</td>
                <td><span style="color:var(--${c})">${esc(r.status)}</span></td>
                <td style="max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px" title="${esc(r.result || '')}">${esc(result)}</td>
                <td style="font-size:11px;color:var(--text-dim)">${dur}</td>
            </tr>`;
        }).join('');
    }

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    window.trgToggle = async function(name) {
        await api(`/api/triggers/${name}/toggle`, { method: 'POST' });
        loadTriggers();
    };

    window.trgTest = async function(name) {
        const raw = prompt('Test payload (JSON):', '{"event": "test"}');
        if (raw === null) return;
        let payload = {};
        try { payload = JSON.parse(raw || '{}'); } catch { alert('Invalid JSON'); return; }
        const res = await api(`/api/triggers/${name}/test`, {
            method: 'POST',
            body: JSON.stringify(payload),
        });
        if (res) alert(`Status: ${res.status} — check Recent firings in a few seconds.`);
        setTimeout(loadFirings, 1500);
    };

    window.trgDelete = async function(name) {
        if (!confirm(`Delete trigger '${name}'?`)) return;
        await api(`/api/triggers/${name}`, { method: 'DELETE' });
        loadTriggers();
    };
})();
