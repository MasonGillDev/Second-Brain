/* Project tracking toolkit — list, detail, tasks/notes/docs, context */
(function () {
    const grid = document.getElementById('projects-grid');
    if (!grid) return;

    const listView = document.getElementById('projects-list-view');
    const detailView = document.getElementById('project-detail-view');
    const backBtn = document.getElementById('projects-back');
    const titleEl = document.getElementById('projects-title');

    let current = null;    // currently open project object
    let editingId = null;  // non-null when the project modal is in edit mode

    function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }

    function relTime(ts) {
        if (!ts) return 'never';
        const s = Date.now() / 1000 - ts;
        if (s < 60) return 'just now';
        if (s < 3600) return Math.floor(s / 60) + 'm ago';
        if (s < 86400) return Math.floor(s / 3600) + 'h ago';
        return Math.floor(s / 86400) + 'd ago';
    }
    function syncText(p) {
        return p.sync_status ? p.sync_status + ' · ' + relTime(p.last_synced_at) : 'never synced';
    }

    // ---------------------------------------------------------------- list view

    async function loadList() {
        showList();
        const data = await api('/api/projects');
        if (!data) return;
        grid.innerHTML = '';
        if (!data.projects.length) {
            grid.innerHTML = '<p style="color:var(--text-secondary);padding:2rem;">No projects yet. Click “New Project”.</p>';
            return;
        }
        data.projects.forEach(p => grid.appendChild(card(p)));
    }

    function card(p) {
        const el = document.createElement('div');
        el.className = 'dashboard-card';
        el.style.cursor = 'pointer';
        let badges = '';
        if (p.github_repo) badges += '<span class="dashboard-badge">' + esc(p.github_repo) + '</span>';
        el.innerHTML =
            '<div class="dashboard-card-header">' +
                '<h3 class="dashboard-card-title">' + esc(p.name) + '</h3>' +
                '<div class="dashboard-card-badges">' + badges + '</div>' +
            '</div>' +
            '<p class="dashboard-card-desc">' + esc(p.path || '—') + '</p>' +
            '<div class="proj-card-stats">' +
                '<span>' + p.open_task_count + '/' + p.task_count + ' open tasks</span>' +
                '<span>' + p.note_count + ' notes</span>' +
                '<span>' + (p.sync_status ? 'sync: ' + esc(p.sync_status) : 'unsynced') + '</span>' +
            '</div>';
        el.onclick = () => openDetail(p.id);
        return el;
    }

    function showList() {
        listView.style.display = '';
        detailView.style.display = 'none';
        backBtn.style.display = 'none';
        titleEl.textContent = 'Projects';
        current = null;
    }

    function showDetail() {
        listView.style.display = 'none';
        detailView.style.display = '';
        backBtn.style.display = '';
    }

    // -------------------------------------------------------------- detail view

    async function openDetail(id) {
        const data = await api('/api/projects/' + id);
        if (!data || data.error) return;
        current = data.project;
        showDetail();
        titleEl.textContent = data.project.name;
        renderDetail(data.project, data.tasks, data.notes);
        loadDocs(id);
    }

    function refresh() { if (current) openDetail(current.id); }

    function metaRow(label, val) {
        return '<div class="proj-meta-row"><span class="proj-meta-label">' + label + '</span>' +
               '<span class="proj-meta-val">' + esc(val || '—') + '</span></div>';
    }

    const STATUSES = ['todo', 'in_progress', 'done'];
    const PRIORITIES = ['low', 'med', 'high'];

    function select(name, value, options) {
        return '<select class="input-field proj-inline-select" data-field="' + name + '">' +
            options.map(o => '<option value="' + o + '"' + (o === value ? ' selected' : '') + '>' + o + '</option>').join('') +
            '</select>';
    }

    function taskRow(t) {
        const issue = t.github_issue
            ? (/^https?:/.test(t.github_issue)
                ? '<a href="' + esc(t.github_issue) + '" target="_blank" class="proj-issue-link">issue ↗</a>'
                : esc(t.github_issue))
            : '<button class="btn-secondary btn-sm proj-push" data-id="' + t.id + '">Push to GitHub</button>';
        return '<tr data-id="' + t.id + '" class="status-' + esc(t.status) + '">' +
            '<td>' + esc(t.name) + (t.description ? '<div class="proj-task-desc">' + esc(t.description) + '</div>' : '') + '</td>' +
            '<td>' + select('status', t.status, STATUSES) + '</td>' +
            '<td>' + select('priority', t.priority, PRIORITIES) + '</td>' +
            '<td class="proj-issue-cell">' + issue + '</td>' +
            '<td><button class="btn-danger btn-sm proj-task-del" data-id="' + t.id + '">✕</button></td>' +
            '</tr>';
    }

    function renderDetail(p, tasks, notes) {
        const tasksBody = tasks.length
            ? tasks.map(taskRow).join('')
            : '<tr><td colspan="5" style="color:var(--text-tertiary)">No tasks yet.</td></tr>';
        const notesBody = notes.length
            ? notes.map(n => '<div class="proj-note" data-id="' + n.id + '">' +
                '<div class="proj-note-head"><strong>' + esc(n.name || '(untitled)') + '</strong>' +
                '<button class="btn-danger btn-sm proj-note-del" data-id="' + n.id + '">✕</button></div>' +
                '<div>' + esc(n.description) + '</div></div>').join('')
            : '<p style="color:var(--text-tertiary)">No notes yet.</p>';

        detailView.innerHTML =
            '<div class="proj-detail-grid">' +
                '<div class="proj-meta">' +
                    metaRow('GitHub', p.github_repo) +
                    metaRow('Machine', p.dev_machine) +
                    metaRow('Path', p.path) +
                    metaRow('Docs', p.docs_path) +
                    metaRow('Similar', p.similar_projects) +
                    '<div class="proj-meta-row"><span class="proj-meta-label">Git sync</span>' +
                        '<span class="proj-meta-val" id="proj-sync-state">' + esc(syncText(p)) + '</span></div>' +
                    '<label class="proj-autosync"><input type="checkbox" id="proj-autosync"' +
                        (p.auto_sync ? ' checked' : '') + '> Auto-sync</label>' +
                    '<div class="proj-meta-actions">' +
                        '<button class="btn-secondary btn-sm" id="proj-edit">Edit</button>' +
                        '<button class="btn-secondary btn-sm" id="proj-pull">Pull now</button>' +
                        '<button class="btn-danger btn-sm" id="proj-delete">Delete project</button>' +
                    '</div>' +
                '</div>' +
                '<div class="proj-context-pane">' +
                    '<div class="proj-section-head"><h3>Context</h3>' +
                        '<button class="btn-primary btn-sm" id="proj-gather">Gather Context</button></div>' +
                    '<pre class="proj-viewer" id="context-body">Click “Gather Context” to pull GitHub, Claude Hub, docs &amp; tasks together.</pre>' +
                '</div>' +
            '</div>' +

            '<div class="proj-section">' +
                '<div class="proj-section-head"><h3>Search</h3>' +
                    '<button class="btn-secondary btn-sm" id="proj-reindex">Reindex</button></div>' +
                '<div class="proj-search-bar">' +
                    '<input type="text" id="proj-search-input" class="input-field" placeholder="Search docs, tasks, notes, commits…">' +
                    '<select id="proj-search-type" class="input-field" style="width:auto">' +
                        '<option value="">all</option><option value="doc">docs</option>' +
                        '<option value="task">tasks</option><option value="note">notes</option>' +
                        '<option value="commit">commits</option>' +
                    '</select>' +
                    '<button class="btn-primary btn-sm" id="proj-search-btn">Search</button>' +
                '</div>' +
                '<div id="proj-search-results"></div>' +
            '</div>' +

            '<div class="proj-section">' +
                '<div class="proj-section-head"><h3>Tasks</h3>' +
                    '<button class="btn-primary btn-sm" id="proj-add-task">+ Add Task</button></div>' +
                '<table class="data-table proj-tasks-table"><thead><tr>' +
                    '<th>Name</th><th>Status</th><th>Priority</th><th>GitHub</th><th></th>' +
                '</tr></thead><tbody id="proj-tasks-body">' + tasksBody + '</tbody></table>' +
            '</div>' +

            '<div class="proj-section">' +
                '<div class="proj-section-head"><h3>Notes</h3>' +
                    '<button class="btn-primary btn-sm" id="proj-add-note">+ Add Note</button></div>' +
                '<div id="proj-notes-list">' + notesBody + '</div>' +
            '</div>' +

            '<div class="proj-section">' +
                '<div class="proj-section-head"><h3>Docs</h3></div>' +
                '<div id="proj-docs-list"><p style="color:var(--text-tertiary)">Loading…</p></div>' +
            '</div>';

        wireDetail();
    }

    function wireDetail() {
        document.getElementById('proj-add-task').onclick = () => openModal('task-proj-modal');
        document.getElementById('proj-add-note').onclick = () => openModal('note-proj-modal');
        document.getElementById('proj-gather').onclick = gatherContext;
        document.getElementById('proj-edit').onclick = openEditProject;
        document.getElementById('proj-delete').onclick = deleteProject;
        document.getElementById('proj-pull').onclick = pullNow;
        document.getElementById('proj-autosync').onchange = (e) =>
            api('/api/projects/' + current.id + '/auto-sync', { method: 'POST', body: JSON.stringify({ on: e.target.checked }) });
        document.getElementById('proj-reindex').onclick = reindex;
        document.getElementById('proj-search-btn').onclick = runSearch;
        document.getElementById('proj-search-input').addEventListener('keydown', e => { if (e.key === 'Enter') runSearch(); });

        const body = document.getElementById('proj-tasks-body');
        body.querySelectorAll('.proj-inline-select').forEach(sel => {
            sel.onchange = () => {
                const tid = sel.closest('tr').dataset.id;
                const patch = {}; patch[sel.dataset.field] = sel.value;
                api('/api/projects/tasks/' + tid, { method: 'PUT', body: JSON.stringify(patch) }).then(refresh);
            };
        });
        body.querySelectorAll('.proj-push').forEach(btn => {
            btn.onclick = async () => {
                btn.disabled = true; btn.textContent = 'Pushing…';
                const r = await api('/api/projects/tasks/' + btn.dataset.id + '/push-github', { method: 'POST' });
                if (r && r.error) { alert('Could not create issue: ' + r.error); btn.disabled = false; btn.textContent = 'Push to GitHub'; }
                else refresh();
            };
        });
        body.querySelectorAll('.proj-task-del').forEach(btn => {
            btn.onclick = () => {
                if (!confirm('Delete this task?')) return;
                api('/api/projects/tasks/' + btn.dataset.id, { method: 'DELETE' }).then(refresh);
            };
        });
        document.querySelectorAll('.proj-note-del').forEach(btn => {
            btn.onclick = () => {
                if (!confirm('Delete this note?')) return;
                api('/api/projects/notes/' + btn.dataset.id, { method: 'DELETE' }).then(refresh);
            };
        });
    }

    async function loadDocs(id) {
        const data = await api('/api/projects/' + id + '/docs');
        const list = document.getElementById('proj-docs-list');
        if (!list) return;
        if (!data || data.error || !data.docs || !data.docs.length) {
            list.innerHTML = '<p style="color:var(--text-tertiary)">' +
                (data && data.docs_path ? 'No docs found under ' + esc(data.docs_path) + '.' : 'No docs_path set for this project.') + '</p>';
            return;
        }
        list.innerHTML = '<ul class="proj-docs">' + data.docs.map(d =>
            '<li><a href="#" class="proj-doc" data-file="' + esc(d) + '">' + esc(d) + '</a></li>').join('') + '</ul>';
        list.querySelectorAll('.proj-doc').forEach(a => {
            a.onclick = (e) => { e.preventDefault(); viewDoc(id, a.dataset.file); };
        });
    }

    async function viewDoc(id, filename) {
        const safe = encodeURIComponent(filename).replace(/%2F/g, '/');
        const data = await api('/api/projects/' + id + '/docs/' + safe);
        document.getElementById('viewer-title').textContent = filename;
        document.getElementById('viewer-body').textContent = (data && data.text) || (data && data.error) || '(empty)';
        openModal('proj-viewer-modal');
    }

    async function gatherContext() {
        const pre = document.getElementById('context-body');
        const btn = document.getElementById('proj-gather');
        pre.textContent = 'Gathering context… (GitHub + Claude Hub + docs)';
        btn.disabled = true;
        const data = await api('/api/projects/' + current.id + '/context');
        btn.disabled = false;
        pre.textContent = (data && data.text) || 'Failed to gather context.';
    }

    function deleteProject() {
        if (!confirm('Delete project “' + current.name + '” and all its tasks/notes?')) return;
        api('/api/projects/' + current.id, { method: 'DELETE' }).then(loadList);
    }

    async function pullNow() {
        const btn = document.getElementById('proj-pull');
        const label = btn.textContent;
        btn.disabled = true; btn.textContent = 'Pulling…';
        const r = await api('/api/projects/' + current.id + '/pull', { method: 'POST' });
        btn.disabled = false; btn.textContent = label;
        if (r && r.project) {
            current = r.project;
            const el = document.getElementById('proj-sync-state');
            if (el) el.textContent = syncText(r.project);
        } else if (r && r.error) {
            alert(r.error);
        }
    }

    // --------------------------------------------------------------- knowledge search

    async function reindex() {
        const btn = document.getElementById('proj-reindex');
        const box = document.getElementById('proj-search-results');
        const label = btn.textContent;
        btn.disabled = true; btn.textContent = 'Indexing…';
        const r = await api('/api/projects/' + current.id + '/reindex', { method: 'POST' });
        btn.disabled = false; btn.textContent = label;
        if (r && r.counts) {
            const c = r.counts;
            box.innerHTML = '<p class="proj-search-note">Indexed ' + c.docs + ' doc chunks · ' +
                c.tasks + ' tasks · ' + c.notes + ' notes · ' + c.commits + ' commits.</p>';
        } else if (r && r.error) {
            box.innerHTML = '<p class="proj-search-note">' + esc(r.error) + '</p>';
        }
    }

    async function runSearch() {
        const q = document.getElementById('proj-search-input').value.trim();
        const type = document.getElementById('proj-search-type').value;
        const box = document.getElementById('proj-search-results');
        if (!q) { box.innerHTML = ''; return; }
        box.innerHTML = '<p class="proj-search-note">Searching…</p>';
        const r = await api('/api/projects/' + current.id + '/search?q=' + encodeURIComponent(q) + (type ? '&type=' + type : ''));
        if (!r) return;
        if (r.error) { box.innerHTML = '<p class="proj-search-note">' + esc(r.error) + '</p>'; return; }
        if (!r.results.length) { box.innerHTML = '<p class="proj-search-note">No matches. Try Reindex if you just added content.</p>'; return; }
        box.innerHTML = r.results.map(renderHit).join('');
        box.querySelectorAll('.proj-hit[data-doc]').forEach(el => {
            el.style.cursor = 'pointer';
            el.onclick = () => viewDoc(current.id, el.dataset.doc);
        });
    }

    function renderHit(h) {
        const docAttr = h.source_type === 'doc' ? ' data-doc="' + esc(h.ref) + '"' : '';
        return '<div class="proj-hit"' + docAttr + '>' +
            '<div class="proj-hit-head">' +
                '<span class="proj-hit-type proj-hit-' + esc(h.source_type) + '">' + esc(h.source_type) + '</span>' +
                '<span class="proj-hit-title">' + esc(h.title || h.ref) + '</span>' +
                '<span class="proj-hit-score">' + h.relevance.toFixed(2) + '</span>' +
            '</div>' +
            '<div class="proj-hit-snippet">' + esc(h.snippet) + '</div>' +
        '</div>';
    }

    // ------------------------------------------------------------------ modals

    function openModal(id) { document.getElementById(id).style.display = 'flex'; }
    function closeModal(id) { document.getElementById(id).style.display = 'none'; }

    const PM_FIELDS = { 'pm-name': 'name', 'pm-repo': 'github_repo', 'pm-machine': 'dev_machine',
        'pm-path': 'path', 'pm-docs': 'docs_path', 'pm-similar': 'similar_projects' };

    // New project (create mode)
    document.getElementById('project-new-btn').onclick = () => {
        editingId = null;
        Object.keys(PM_FIELDS).forEach(i => document.getElementById(i).value = '');
        document.getElementById('pm-title').textContent = 'New Project';
        document.getElementById('pm-save').textContent = 'Create';
        openModal('project-modal');
    };

    // Edit project (edit mode) — prefills from the open project
    function openEditProject() {
        editingId = current.id;
        document.getElementById('pm-name').value = current.name || '';
        document.getElementById('pm-repo').value = current.github_repo || '';
        document.getElementById('pm-machine').value = current.dev_machine || '';
        document.getElementById('pm-path').value = current.path || '';
        document.getElementById('pm-docs').value = current.docs_path || '';
        document.getElementById('pm-similar').value = current.similar_projects || '';
        document.getElementById('pm-title').textContent = 'Edit Project';
        document.getElementById('pm-save').textContent = 'Save';
        openModal('project-modal');
    }

    document.getElementById('pm-cancel').onclick = () => { editingId = null; closeModal('project-modal'); };
    document.getElementById('pm-save').onclick = async () => {
        const payload = {};
        Object.entries(PM_FIELDS).forEach(([id, key]) => { payload[key] = document.getElementById(id).value.trim(); });
        if (!payload.name) { alert('Project name is required.'); return; }
        const r = editingId
            ? await api('/api/projects/' + editingId, { method: 'PUT', body: JSON.stringify(payload) })
            : await api('/api/projects', { method: 'POST', body: JSON.stringify(payload) });
        if (r && r.error) { alert(r.error); return; }
        closeModal('project-modal');
        const wasEditing = editingId;
        editingId = null;
        if (wasEditing) openDetail(wasEditing); else loadList();
    };

    // New task
    document.getElementById('tm-cancel').onclick = () => closeModal('task-proj-modal');
    document.getElementById('tm-save').onclick = async () => {
        const name = document.getElementById('tm-name').value.trim();
        if (!name) { alert('Task name is required.'); return; }
        const payload = {
            name: name,
            description: document.getElementById('tm-desc').value.trim(),
            priority: document.getElementById('tm-priority').value,
        };
        const r = await api('/api/projects/' + current.id + '/tasks', { method: 'POST', body: JSON.stringify(payload) });
        if (r && r.error) { alert(r.error); return; }
        ['tm-name', 'tm-desc'].forEach(i => document.getElementById(i).value = '');
        closeModal('task-proj-modal');
        refresh();
    };

    // New note
    document.getElementById('nm-cancel').onclick = () => closeModal('note-proj-modal');
    document.getElementById('nm-save').onclick = async () => {
        const payload = {
            name: document.getElementById('nm-name').value.trim(),
            description: document.getElementById('nm-desc').value.trim(),
        };
        if (!payload.name && !payload.description) { alert('Add a title or note text.'); return; }
        const r = await api('/api/projects/' + current.id + '/notes', { method: 'POST', body: JSON.stringify(payload) });
        if (r && r.error) { alert(r.error); return; }
        ['nm-name', 'nm-desc'].forEach(i => document.getElementById(i).value = '');
        closeModal('note-proj-modal');
        refresh();
    };

    document.getElementById('viewer-close').onclick = () => closeModal('proj-viewer-modal');

    // Close modals on overlay click
    document.querySelectorAll('#tab-projects .modal-overlay').forEach(ov => {
        ov.addEventListener('click', e => { if (e.target === ov) ov.style.display = 'none'; });
    });

    backBtn.addEventListener('click', showList);
    window.addEventListener('tab:projects', loadList);
})();
