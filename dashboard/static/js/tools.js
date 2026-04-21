/* Tool management */
(function() {
    const grid = document.getElementById('tools-grid');

    window.addEventListener('tab:tools', loadTools);

    async function loadTools() {
        const data = await api('/api/tools');
        if (!data) return;

        grid.innerHTML = Object.entries(data.servers).map(([name, info]) => `
            <div class="tool-card">
                <div class="tool-card-header">
                    <span class="tool-card-name">${name}</span>
                    <label class="toggle">
                        <input type="checkbox" ${info.enabled ? 'checked' : ''} onchange="toggleServer('${name}')">
                        <span class="toggle-track"></span>
                        <span class="toggle-thumb"></span>
                    </label>
                </div>
                ${info.description ? `<p style="font-size:12px;color:var(--text-dim);margin-bottom:10px">${info.description}</p>` : ''}
                <div class="tool-list">
                    ${info.tools.map(t => `<span class="tool-tag">${t}</span>`).join('')}
                </div>
            </div>
        `).join('');
    }

    window.toggleServer = async function(name) {
        await api(`/api/tools/${name}/toggle`, { method: 'POST' });
    };
})();
