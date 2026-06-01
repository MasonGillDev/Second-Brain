/* Activity log — reads from SQLite via /api/logs */
(function() {
    const stream = document.getElementById('log-stream');
    const liveToggle = document.getElementById('logs-live');
    const sourceFilter = document.getElementById('logs-source-filter');
    const levelFilter = document.getElementById('logs-level-filter');
    let nextId = 0;
    let polling = false;
    let loaded = false;

    let expandAll = false;

    function sourceClass(source) {
        const map = {
            tool: 'log-line-tool',
            agent: 'log-line-agent',
            memory: 'log-line-memory',
            sleep: 'log-line-sleep',
            tokens: 'log-line-tokens',
        };
        return map[source] || '';
    }

    function levelClass(level) {
        if (level === 'error') return 'log-line-error';
        if (level === 'warning') return 'log-line-warning';
        return '';
    }

    function renderEntry(entry) {
        const line = document.createElement('div');
        line.className = 'log-entry ' + (levelClass(entry.level) || sourceClass(entry.source));
        const ts = new Date(entry.timestamp * 1000).toLocaleTimeString();
        const badge = entry.source ? `<span class="log-source-tag">${entry.source}</span>` : '';
        const hasDetails = !!entry.details;
        const caret = hasDetails ? `<span class="log-caret">▶</span>` : `<span class="log-caret-spacer"></span>`;

        const row = document.createElement('div');
        row.className = 'log-row';
        row.innerHTML = `${caret}<span class="log-ts">${ts}</span>${badge}<span class="log-msg">${escapeHtml(entry.message)}</span>`;
        line.appendChild(row);

        if (hasDetails) {
            line.classList.add('has-details');
            const pre = document.createElement('pre');
            pre.className = 'log-details';
            pre.textContent = entry.details;
            line.appendChild(pre);
            row.style.cursor = 'pointer';
            row.addEventListener('click', () => line.classList.toggle('expanded'));
            if (expandAll) line.classList.add('expanded');
        }
        return line;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async function loadInitial() {
        const source = sourceFilter.value;
        const level = levelFilter.value;
        let url = `/api/logs?limit=200`;
        if (source) url += `&source=${source}`;
        if (level) url += `&level=${level}`;

        try {
            const data = await api(url);
            if (!data || !data.entries) return;
            stream.innerHTML = '';
            // Entries come newest-first from the range query, reverse for chronological display
            const entries = data.entries.reverse();
            entries.forEach(entry => stream.appendChild(renderEntry(entry)));
            nextId = data.next_id || 0;
            stream.scrollTop = stream.scrollHeight;
            loaded = true;
        } catch (e) {}
    }

    async function poll() {
        if (!polling) return;
        try {
            const source = sourceFilter.value;
            const level = levelFilter.value;
            let url = `/api/logs?since_id=${nextId}&limit=50`;
            if (source) url += `&source=${source}`;
            if (level) url += `&level=${level}`;

            const data = await api(url);
            if (data && data.entries && data.entries.length > 0) {
                data.entries.forEach(entry => stream.appendChild(renderEntry(entry)));
                nextId = data.next_id;
                if (liveToggle.checked) {
                    stream.scrollTop = stream.scrollHeight;
                }
            }
        } catch (e) {}
        if (polling) setTimeout(poll, 1000);
    }

    function start() {
        if (!loaded) loadInitial();
        if (!polling && liveToggle.checked) {
            polling = true;
            poll();
        }
    }

    function stop() {
        polling = false;
    }

    window.addEventListener('tab:logs', start);

    document.querySelectorAll('.nav-btn[data-tab]').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.tab !== 'logs') stop();
        });
    });

    liveToggle.addEventListener('change', () => {
        if (liveToggle.checked) {
            polling = true;
            poll();
        } else {
            stop();
        }
    });

    // Re-fetch when filters change
    sourceFilter.addEventListener('change', () => { loaded = false; nextId = 0; loadInitial(); });
    levelFilter.addEventListener('change', () => { loaded = false; nextId = 0; loadInitial(); });

    document.getElementById('logs-clear').addEventListener('click', () => {
        stream.innerHTML = '';
        nextId = 0;
        loaded = false;
    });

    document.getElementById('logs-expand-all').addEventListener('click', (e) => {
        expandAll = !expandAll;
        e.target.textContent = expandAll ? 'Collapse all' : 'Expand all';
        stream.querySelectorAll('.log-entry.has-details').forEach(el => {
            el.classList.toggle('expanded', expandAll);
        });
    });
})();
