/* Memory management */
(function() {
    let currentCollection = 'long_term';
    const tbody = document.getElementById('memory-tbody');
    const statsBar = document.getElementById('memory-stats');
    const modal = document.getElementById('memory-modal');
    let editingId = null;

    function isCodeCollection() {
        return currentCollection === 'code_context';
    }

    // Collection tabs
    document.getElementById('collection-tabs').addEventListener('click', (e) => {
        const tab = e.target.closest('.col-tab');
        if (!tab) return;
        document.querySelectorAll('.col-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentCollection = tab.dataset.col;

        // Toggle add button visibility (can't add to code_context manually)
        document.getElementById('memory-add-btn').style.display = isCodeCollection() ? 'none' : '';

        loadMemories();
    });

    // Search
    document.getElementById('memory-search-btn').addEventListener('click', searchMemories);
    document.getElementById('memory-search').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') searchMemories();
    });

    // Add button
    document.getElementById('memory-add-btn').addEventListener('click', () => {
        editingId = null;
        document.getElementById('memory-modal-title').textContent = 'Add Memory';
        document.getElementById('memory-modal-text').value = '';
        document.getElementById('memory-modal-category').value = 'general';
        modal.style.display = '';
    });

    // Modal cancel/save
    document.getElementById('memory-modal-cancel').addEventListener('click', () => modal.style.display = 'none');
    document.getElementById('memory-modal-save').addEventListener('click', saveMemory);

    async function loadMemories() {
        if (isCodeCollection()) {
            const data = await api('/api/memory/code/list?limit=100');
            if (!data) return;
            renderCodeTable(data.memories);
        } else {
            const data = await api(`/api/memory/${currentCollection}?limit=100`);
            if (!data) return;
            renderTable(data.memories);
        }
        loadStats();
    }

    async function searchMemories() {
        const q = document.getElementById('memory-search').value.trim();
        if (!q) { loadMemories(); return; }

        if (isCodeCollection()) {
            const data = await api(`/api/memory/code/search?q=${encodeURIComponent(q)}&top_k=20`);
            if (!data) return;
            renderCodeTable(data.results);
        } else {
            const data = await api(`/api/memory/${currentCollection}/search?q=${encodeURIComponent(q)}&top_k=20`);
            if (!data) return;
            renderTable(data.results);
        }
    }

    async function loadStats() {
        const data = await api('/api/memory/stats');
        if (!data) return;
        const cols = data.collections;
        const max = Math.max(1, ...Object.values(cols));
        statsBar.innerHTML = Object.entries(cols).map(([name, count]) =>
            `<div class="stat-item">
                <span class="stat-count">${name.substring(0, 4)}</span>
                <div class="stat-bar"><div class="stat-bar-fill" style="width:${(count/max)*100}%"></div></div>
                <span class="stat-count">${count}</span>
            </div>`
        ).join('');
    }

    function fmtTime(ts) {
        if (!ts) return '\u2014';
        const d = new Date(ts * 1000);
        return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    }

    function renderTable(memories) {
        // Set standard memory table headers
        document.getElementById('memory-table').querySelector('thead').innerHTML = `<tr>
            <th class="col-id">ID</th>
            <th class="col-text">Text</th>
            <th class="col-cat">Category</th>
            <th class="col-access">Hits</th>
            <th class="col-time">Created</th>
            <th class="col-time">Last Accessed</th>
            <th class="col-actions">Actions</th>
        </tr>`;

        tbody.innerHTML = memories.map(m => {
            const meta = m.metadata || {};
            const cat = meta.category || meta.type || '';
            const hits = meta.access_count || 0;
            const created = fmtTime(meta.created_at);
            const accessed = fmtTime(meta.last_accessed);
            const rel = m.relevance != null ? `<span style="font-family:var(--font-mono);font-size:10px;color:var(--text-tertiary)">${m.relevance.toFixed(3)}</span>` : '';
            return `<tr>
                <td class="col-id">${esc(m.id)}</td>
                <td class="col-text">${esc(m.text)} ${rel}</td>
                <td class="col-cat"><span class="badge cat-${cat}">${cat}</span></td>
                <td class="col-access">${hits}</td>
                <td class="col-time">${created}</td>
                <td class="col-time">${accessed}</td>
                <td class="col-actions">
                    <button class="action-btn" onclick="memoryEdit('${esc(m.id)}', ${JSON.stringify(JSON.stringify(m.text))})">Edit</button>
                    <button class="action-btn delete" onclick="memoryDelete('${esc(m.id)}')">Del</button>
                </td>
            </tr>`;
        }).join('');
    }

    function renderCodeTable(memories) {
        // Set code-specific table headers
        document.getElementById('memory-table').querySelector('thead').innerHTML = `<tr>
            <th style="width:300px">File</th>
            <th>Content</th>
            <th style="width:80px">Type</th>
            <th style="width:60px">Line</th>
            <th style="width:70px">Relevance</th>
        </tr>`;

        if (!memories || memories.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text-tertiary);padding:40px">No code context found. Try a search query.</td></tr>';
            return;
        }

        tbody.innerHTML = memories.map(m => {
            const meta = m.metadata || {};
            const fp = meta.file_path || '';
            const shortPath = fp.split('/').slice(-3).join('/');
            const line = meta.line_number || '';
            const type = meta.type || '';
            const lang = meta.language || '';
            const rel = m.relevance != null ? m.relevance.toFixed(3) : '\u2014';

            const typeBadgeClass = type === 'xml_doc' ? 'cat-user_fact' :
                                   type === 'class_sig' ? 'cat-preference' :
                                   type === 'comment_block' ? 'cat-decision' : 'cat-general';

            return `<tr>
                <td style="font-family:var(--font-mono);font-size:11px;color:var(--text-tertiary);word-break:break-all" title="${esc(fp)}">${esc(shortPath)}</td>
                <td style="font-size:12px">${esc(m.text)}</td>
                <td><span class="badge ${typeBadgeClass}">${type}</span></td>
                <td style="font-family:var(--font-mono);font-size:11px;text-align:center">${line}</td>
                <td style="font-family:var(--font-mono);font-size:11px;text-align:center;color:var(--text-tertiary)">${rel}</td>
            </tr>`;
        }).join('');
    }

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    async function saveMemory() {
        const text = document.getElementById('memory-modal-text').value.trim();
        const category = document.getElementById('memory-modal-category').value;
        if (!text) return;

        if (editingId) {
            await api(`/api/memory/${currentCollection}/${editingId}`, {
                method: 'PUT',
                body: JSON.stringify({ text }),
            });
        } else {
            await api(`/api/memory/${currentCollection}`, {
                method: 'POST',
                body: JSON.stringify({ text, category }),
            });
        }
        modal.style.display = 'none';
        loadMemories();
    }

    // Global functions for inline handlers
    window.memoryEdit = function(id, text) {
        editingId = id;
        document.getElementById('memory-modal-title').textContent = 'Edit Memory';
        document.getElementById('memory-modal-text').value = text;
        modal.style.display = '';
    };

    window.memoryDelete = async function(id) {
        if (!confirm('Delete this memory?')) return;
        await api(`/api/memory/${currentCollection}/${id}`, { method: 'DELETE' });
        loadMemories();
    };

    // Initial load on tab switch
    window.addEventListener('tab:memories', loadMemories);

    // Also load stats on first view
    loadStats();
})();
