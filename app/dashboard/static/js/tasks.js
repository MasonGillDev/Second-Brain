/* Scheduled tasks management */
(function() {
    const tbody = document.getElementById('task-tbody');
    const modal = document.getElementById('task-modal');
    let editingId = null;

    document.getElementById('task-add-btn').addEventListener('click', () => {
        editingId = null;
        document.getElementById('task-modal-title').textContent = 'New Task';
        document.getElementById('task-modal-name').value = '';
        document.getElementById('task-modal-schedule').value = '';
        document.getElementById('task-modal-prompt').value = '';
        modal.style.display = '';
    });

    document.getElementById('task-modal-cancel').addEventListener('click', () => modal.style.display = 'none');
    document.getElementById('task-modal-save').addEventListener('click', saveTask);

    window.addEventListener('tab:tasks', loadTasks);

    async function loadTasks() {
        const data = await api('/api/tasks');
        if (!data) return;
        renderTasks(data.tasks);
    }

    function renderTasks(tasks) {
        tbody.innerHTML = tasks.map(t => {
            const statusCls = t.enabled ? 'green' : 'red';
            const statusTxt = t.enabled ? 'ON' : 'OFF';
            const lastRun = t.last_run ? new Date(t.last_run).toLocaleString() : 'Never';
            return `<tr>
                <td><span class="status-dot" style="background:var(--${statusCls});display:inline-block"></span> ${statusTxt}</td>
                <td style="font-weight:500">${esc(t.name)}</td>
                <td><code style="font-size:11px">${esc(t.schedule)}</code></td>
                <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(t.prompt)}</td>
                <td style="font-size:11px;color:var(--text-dim)">${lastRun}</td>
                <td>
                    <button class="action-btn" onclick="taskToggle('${t.id}')">${t.enabled ? 'Disable' : 'Enable'}</button>
                    <button class="action-btn" onclick="taskEdit('${t.id}', ${JSON.stringify(JSON.stringify(t.name))}, ${JSON.stringify(JSON.stringify(t.schedule))}, ${JSON.stringify(JSON.stringify(t.prompt))})">Edit</button>
                    <button class="action-btn delete" onclick="taskDelete('${t.id}')">Del</button>
                </td>
            </tr>`;
        }).join('');
    }

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s || '';
        return d.innerHTML;
    }

    async function saveTask() {
        const name = document.getElementById('task-modal-name').value.trim();
        const schedule = document.getElementById('task-modal-schedule').value.trim();
        const prompt = document.getElementById('task-modal-prompt').value.trim();
        if (!name || !schedule || !prompt) return;

        if (editingId) {
            await api(`/api/tasks/${editingId}`, {
                method: 'PUT',
                body: JSON.stringify({ name, schedule, prompt }),
            });
        } else {
            await api('/api/tasks', {
                method: 'POST',
                body: JSON.stringify({ name, schedule, prompt }),
            });
        }
        modal.style.display = 'none';
        loadTasks();
    }

    window.taskToggle = async function(id) {
        await api(`/api/tasks/${id}/toggle`, { method: 'POST' });
        loadTasks();
    };

    window.taskEdit = function(id, name, schedule, prompt) {
        editingId = id;
        document.getElementById('task-modal-title').textContent = 'Edit Task';
        document.getElementById('task-modal-name').value = name;
        document.getElementById('task-modal-schedule').value = schedule;
        document.getElementById('task-modal-prompt').value = prompt;
        modal.style.display = '';
    };

    window.taskDelete = async function(id) {
        if (!confirm('Delete this task?')) return;
        await api(`/api/tasks/${id}`, { method: 'DELETE' });
        loadTasks();
    };
})();
