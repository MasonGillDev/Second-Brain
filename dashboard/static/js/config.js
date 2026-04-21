/* Config editor */
(function() {
    const form = document.getElementById('config-form');
    let configData = {};

    window.addEventListener('tab:config', loadConfig);
    document.getElementById('config-save').addEventListener('click', saveConfig);

    async function loadConfig() {
        const data = await api('/api/config');
        if (!data) return;
        configData = data.config;

        // Group by prefix
        const groups = {};
        for (const [key, info] of Object.entries(configData)) {
            const prefix = key.split('_')[0];
            const group = {
                'MODEL': 'Model',
                'TOTAL': 'Context Budget',
                'BUDGET': 'Context Budget',
                'WORKING': 'Conversation',
                'SUMMARIZE': 'Conversation',
                'MAX': 'Limits',
                'CHROMA': 'Storage',
                'RETRIEVAL': 'Retrieval',
                'CHUNK': 'Ingestion',
                'AUTO': 'Memory Extraction',
                'EXTRACT': 'Memory Extraction',
                'IMPORTANCE': 'Memory Extraction',
                'DEDUP': 'Maintenance',
                'CONSOLIDAT': 'Maintenance',
                'CONSOLIDATION': 'Maintenance',
                'SLEEP': 'Sleep Agent',
                'INPUT': 'Cost',
                'OUTPUT': 'Cost',
                'TOKEN': 'Cost',
                'LOG': 'Logging',
                'TOOLS': 'Tools',
                'TELEGRAM': 'Telegram',
            }[prefix] || 'Other';

            if (!groups[group]) groups[group] = [];
            groups[group].push([key, info]);
        }

        form.innerHTML = Object.entries(groups).map(([group, items]) => `
            <div class="config-group">
                <div class="config-group-title">${group}</div>
                ${items.map(([key, info]) => {
                    const cls = info.readonly ? ' config-readonly' : '';
                    let input;
                    if (info.type === 'boolean') {
                        input = `<label class="checkbox-label"><input type="checkbox" data-key="${key}" ${info.value ? 'checked' : ''} ${info.readonly ? 'disabled' : ''}> ${info.value ? 'true' : 'false'}</label>`;
                    } else {
                        input = `<input type="${info.type === 'number' ? 'number' : 'text'}" data-key="${key}" value="${info.value}" step="any" ${info.readonly ? 'disabled' : ''}>`;
                    }
                    return `<div class="config-row${cls}"><span class="config-key">${key}</span><span class="config-value">${input}</span></div>`;
                }).join('')}
            </div>
        `).join('');

        // Update checkbox labels
        form.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.addEventListener('change', () => {
                cb.parentElement.childNodes[1].textContent = ' ' + (cb.checked ? 'true' : 'false');
            });
        });
    }

    async function saveConfig() {
        const updates = {};
        form.querySelectorAll('[data-key]').forEach(el => {
            const key = el.dataset.key;
            const info = configData[key];
            if (!info || info.readonly) return;

            let val;
            if (el.type === 'checkbox') {
                val = el.checked;
            } else if (info.type === 'number') {
                val = el.value.includes('.') ? parseFloat(el.value) : parseInt(el.value);
            } else {
                val = el.value;
            }

            if (val !== info.value) {
                updates[key] = val;
            }
        });

        if (Object.keys(updates).length === 0) return;

        const data = await api('/api/config', {
            method: 'PUT',
            body: JSON.stringify({ updates }),
        });

        if (data && data.status === 'updated') {
            // Update local state
            for (const [k, v] of Object.entries(updates)) {
                if (configData[k]) configData[k].value = v;
            }
            alert('Config saved: ' + data.applied.join(', '));
        }
    }
})();
