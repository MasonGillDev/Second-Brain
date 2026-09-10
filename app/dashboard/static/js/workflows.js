/* Workflow builder — list + drag-and-drop canvas editor.
 *
 * A workflow is the engine schema: { name, description, params[], steps[], output, surfaces }.
 * Each step is exactly one of: {tool,args} | {prompt} | {speak} | {extract} | {stop} |
 * {workflow,args} | {foreach}. A foreach's nested steps are edited as raw JSON — the
 * canvas stays a flat list; loops don't get their own drag-and-drop sub-canvas.
 * The editor keeps a live in-memory `state.def` as the single source of truth;
 * inputs write into it, and buildDef() serializes it back to the schema.
 */
(function () {
    // ---- elements ----------------------------------------------------------
    const listView = document.getElementById('wf-list-view');
    const editorView = document.getElementById('wf-editor-view');
    const tbody = document.getElementById('wf-tbody');
    const listEmpty = document.getElementById('wf-list-empty');

    const elTriggers = document.getElementById('wf-triggers');
    const elName = document.getElementById('wf-name');
    const elDesc = document.getElementById('wf-desc');
    const elOutput = document.getElementById('wf-output');
    const elSchedulable = document.getElementById('wf-schedulable');
    const elExpose = document.getElementById('wf-expose');
    const paramsEl = document.getElementById('wf-params');
    const paletteListEl = document.getElementById('wf-palette-list');
    const paletteSearch = document.getElementById('wf-palette-search');
    const stepsEl = document.getElementById('wf-steps');
    const stepsEmpty = document.getElementById('wf-steps-empty');
    const editorTitle = document.getElementById('wf-editor-name');
    const saveMsg = document.getElementById('wf-save-msg');

    const testPanel = document.getElementById('wf-test-panel');
    const testParams = document.getElementById('wf-test-params');
    const testRunRow = document.getElementById('wf-test-run-row');
    const testResult = document.getElementById('wf-test-result');

    const jsonModal = document.getElementById('wf-json-modal');
    const jsonText = document.getElementById('wf-json-text');
    const jsonError = document.getElementById('wf-json-error');

    // ---- state -------------------------------------------------------------
    const state = { def: null, palette: null, toolIndex: {}, stepsSortable: null, models: null, defaultModel: '', wfDefs: {} };

    function uid() { return 's' + Math.random().toString(36).slice(2, 9); }
    function esc(s) {
        const d = document.createElement('div'); d.textContent = (s == null ? '' : String(s));
        return d.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;'); // attribute-safe too
    }
    function stepKind(s) { return ('tool' in s) ? 'tool' : ('prompt' in s) ? 'prompt' : ('speak' in s) ? 'speak' : ('shell' in s) ? 'shell' : ('extract' in s) ? 'extract' : ('stop' in s) ? 'stop' : ('foreach' in s) ? 'foreach' : 'workflow'; }
    function stepByUid(u) { return (state.def.steps || []).find(s => s._uid === u); }
    function newBlankDef() {
        return { name: '', description: '', params: [], steps: [], output: '',
                 surfaces: { schedulable: false, expose_as_tool: false } };
    }

    // ---- list view ---------------------------------------------------------
    window.addEventListener('tab:workflows', () => { showList(); loadWorkflows(); });
    document.getElementById('wf-new-btn').addEventListener('click', () => openEditor(null));

    function showList() { listView.style.display = ''; editorView.style.display = 'none'; }
    function showEditor() { listView.style.display = 'none'; editorView.style.display = ''; }

    async function loadWorkflows() {
        const data = await api('/api/workflows');
        if (!data) return;
        const rows = data.workflows || [];
        listEmpty.style.display = rows.length ? 'none' : '';
        tbody.innerHTML = rows.map(w => {
            const s = w.surfaces || {};
            const badges = [
                s.schedulable ? '<span class="badge wf-badge">⏰ scheduled</span>' : '',
                s.expose_as_tool ? '<span class="badge wf-badge">🔧 tool</span>' : '',
            ].join(' ');
            const nm = esc(w.name);
            return `<tr>
                <td><a class="wf-link" onclick="wfEdit('${nm}')">${nm}</a></td>
                <td class="wf-desc-cell">${esc(w.description)}</td>
                <td>${w.steps}</td>
                <td>${badges}</td>
                <td class="col-actions">
                    <button class="action-btn" onclick="wfEdit('${nm}')">Edit</button>
                    <button class="action-btn delete" onclick="wfDelete('${nm}')">Delete</button>
                </td></tr>`;
        }).join('');
    }

    window.wfEdit = (name) => openEditor(name);
    window.wfDelete = async (name) => {
        if (!confirm(`Delete workflow "${name}"?`)) return;
        await api('/api/workflows/' + encodeURIComponent(name), { method: 'DELETE' });
        loadWorkflows();
    };

    // ---- editor ------------------------------------------------------------
    document.getElementById('wf-back-btn').addEventListener('click', () => { showList(); loadWorkflows(); });
    document.getElementById('wf-save-btn').addEventListener('click', saveWorkflow);
    document.getElementById('wf-test-btn').addEventListener('click', openTestPanel);
    document.getElementById('wf-json-btn').addEventListener('click', openJson);
    document.getElementById('wf-add-param').addEventListener('click', () => {
        state.def.params.push({ name: '', required: false, default: '', description: '' });
        renderParams();
    });

    // static meta inputs write straight into the model
    elName.addEventListener('input', () => { state.def.name = elName.value; });
    elDesc.addEventListener('input', () => { state.def.description = elDesc.value; });
    elOutput.addEventListener('input', () => { state.def.output = elOutput.value; });
    elTriggers.addEventListener('input', () => {
        state.def.triggers = elTriggers.value.split('\n').map(t => t.trim()).filter(Boolean);
    });
    elSchedulable.addEventListener('change', () => { state.def.surfaces.schedulable = elSchedulable.checked; });
    elExpose.addEventListener('change', () => { state.def.surfaces.expose_as_tool = elExpose.checked; });

    async function openEditor(name) {
        showEditor();
        saveMsg.style.display = 'none';
        testPanel.style.display = 'none';
        state.wfDefs = {}; // sub-workflow previews: refetch fresh per editing session
        await ensurePalette();
        if (name) {
            const def = await api('/api/workflows/' + encodeURIComponent(name));
            state.def = def && !def.error ? def : newBlankDef();
        } else {
            state.def = newBlankDef();
        }
        normalizeDef(state.def);
        editorTitle.textContent = name || 'New Workflow';
        fillMeta();
        renderParams();
        renderPalette();
        renderSteps();
    }

    function normalizeDef(d) {
        d.params = d.params || [];
        d.steps = d.steps || [];
        d.surfaces = d.surfaces || { schedulable: false, expose_as_tool: false };
        d.steps.forEach(s => {
            s._uid = uid();
            if ('workflow' in s) {
                s._args = Object.entries(s.args || {}).map(([k, v]) => ({ k, v: String(v) }));
            }
            if ('tool' in s) s.args = s.args || {};
            if ('extract' in s) {
                s.extract = s.extract || {};
                s.extract.input = s.extract.input || '';
                s.extract.fields = s.extract.fields || [];
            }
            if ('stop' in s) {
                s.stop = s.stop || {};
                s.stop.when = s.stop.when || '';
                s.stop.output = s.stop.output || '';
            }
            if ('shell' in s) {
                s.shell = s.shell || {};
                s.shell.command = s.shell.command || '';
                s.shell.cwd = s.shell.cwd || '';
                s.shell.timeout = s.shell.timeout || '';
            }
            if ('foreach' in s) {
                s.foreach = s.foreach || {};
                s.foreach.items = s.foreach.items || '';
                s.foreach.as = s.foreach.as || '';
                s.foreach.join = s.foreach.join || '';
                s.foreach.steps = s.foreach.steps || [];
                // The nested steps are edited as raw JSON; _bodyText holds the
                // text as typed, s.foreach.steps the last VALID parse of it.
                s._bodyText = JSON.stringify(s.foreach.steps, null, 2);
            }
        });
    }

    function fillMeta() {
        elName.value = state.def.name || '';
        elDesc.value = state.def.description || '';
        elOutput.value = state.def.output || '';
        elTriggers.value = (state.def.triggers || []).join('\n');
        elSchedulable.checked = !!state.def.surfaces.schedulable;
        elExpose.checked = !!state.def.surfaces.expose_as_tool;
    }

    // ---- params editor -----------------------------------------------------
    function renderParams() {
        const ps = state.def.params || [];
        paramsEl.innerHTML = ps.length ? ps.map((p, i) => `
            <div class="wf-param-row" data-idx="${i}">
                <input class="input-field" data-prole="name" placeholder="name" value="${esc(p.name)}">
                <input class="input-field" data-prole="default" placeholder="default (optional)" value="${esc(p.default)}">
                <input class="input-field" data-prole="description" placeholder="description" value="${esc(p.description)}">
                <label class="checkbox-label"><input type="checkbox" data-prole="required" ${p.required ? 'checked' : ''}> req</label>
                <button class="action-btn delete" data-paction="del">×</button>
            </div>`).join('') : '<div class="wf-hint">No parameters. Add one to accept inputs (referenced as {{name}}).</div>';
    }
    paramsEl.addEventListener('input', (e) => {
        const row = e.target.closest('.wf-param-row'); if (!row) return;
        const p = state.def.params[+row.dataset.idx]; const role = e.target.dataset.prole;
        if (role === 'name') p.name = e.target.value;
        else if (role === 'default') p.default = e.target.value;
        else if (role === 'description') p.description = e.target.value;
    });
    paramsEl.addEventListener('change', (e) => {
        if (e.target.dataset.prole === 'required') {
            const row = e.target.closest('.wf-param-row');
            state.def.params[+row.dataset.idx].required = e.target.checked;
        }
    });
    paramsEl.addEventListener('click', (e) => {
        if (e.target.dataset.paction === 'del') {
            const row = e.target.closest('.wf-param-row');
            state.def.params.splice(+row.dataset.idx, 1);
            renderParams();
        }
    });

    // ---- palette -----------------------------------------------------------
    async function ensurePalette() {
        if (state.palette) return;
        const data = await api('/api/workflows/palette');
        state.palette = data || { servers: {}, workflows: [] };
        state.toolIndex = {};
        Object.values(state.palette.servers || {}).forEach(srv => {
            (srv.tools || []).forEach(t => { state.toolIndex[t.full_name] = t; });
        });
        await ensureModels();
    }

    async function ensureModels() {
        if (state.models) return;
        const data = await api('/api/workflows/models');
        state.models = (data && data.models) || [];
        state.defaultModel = (data && data.default) || '';
        let dl = document.getElementById('wf-models');
        if (!dl) { dl = document.createElement('datalist'); dl.id = 'wf-models'; document.body.appendChild(dl); }
        dl.innerHTML = state.models.map(m => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join('');
    }

    // A per-step model override (prompt/extract only — those make isolated LLM
    // calls). Empty = the workflow default (config.MODEL). Typeahead via datalist.
    function modelInput(s) {
        const def = state.defaultModel || 'default';
        return `<input class="input-field wf-model" data-role="model" list="wf-models"
            placeholder="model — default: ${esc(def)}" value="${esc(s.model || '')}">`;
    }

    function renderPalette() {
        const servers = state.palette.servers || {};
        let html = `
            <div class="wf-pal-group">
                <div class="wf-pal-group-head">Nodes</div>
                <div class="wf-pal-item wf-pal-special" data-node="prompt" data-full=""
                     title="An isolated LLM step over only the workflow context">💬 Prompt</div>
                <div class="wf-pal-item wf-pal-special" data-node="speak" data-full=""
                     title="Say the text aloud through the voice assistant">🔊 Speak</div>
                <div class="wf-pal-item wf-pal-special" data-node="shell" data-full=""
                     title="Run any shell command on this machine as your user. Unrestricted — no allow/deny list, no sandbox. Use with care, especially on workflows that auto-trigger from voice or a schedule.">🖥️ Shell</div>
                <div class="wf-pal-item wf-pal-special" data-node="extract" data-full=""
                     title="Pull named variables out of a step's data as JSON">🔎 Extract</div>
                <div class="wf-pal-item wf-pal-special" data-node="stop" data-full=""
                     title="End the workflow early when a condition passes">🛑 Stop</div>
                <div class="wf-pal-item wf-pal-special" data-node="foreach" data-full=""
                     title="Run nested steps once per item of a list (a for-loop). Items come from a JSON array or newline/comma-separated text — usually a prior step's output.">🔁 Loop</div>
                <div class="wf-pal-item wf-pal-special" data-node="workflow" data-full=""
                     title="Run another workflow as a step">🧩 Workflow</div>
            </div>`;
        Object.keys(servers).sort().forEach(sname => {
            const srv = servers[sname];
            const tools = (srv.tools || []).map(t => `
                <div class="wf-pal-item" data-node="tool" data-full="${esc(t.full_name)}"
                     data-search="${esc((t.name + ' ' + t.description).toLowerCase())}"
                     title="${esc(t.description)}">🔧 ${esc(t.name)}</div>`).join('');
            html += `<div class="wf-pal-group">
                <div class="wf-pal-group-head">${esc(sname)}</div>${tools}</div>`;
        });
        paletteListEl.innerHTML = html;

        if (typeof Sortable === 'undefined') {
            console.error('[workflows] SortableJS failed to load — drag-and-drop disabled.');
            return;
        }
        // SortableJS only manages DIRECT children. Our items live inside per-server
        // .wf-pal-group wrappers, so init a clone-source Sortable on each GROUP
        // (not on the list) — otherwise the items aren't draggable at all.
        paletteListEl.querySelectorAll('.wf-pal-group').forEach(group => {
            new Sortable(group, {
                group: { name: 'wf', pull: 'clone', put: false },
                sort: false, animation: 150, draggable: '.wf-pal-item',
            });
        });
    }

    paletteSearch.addEventListener('input', () => {
        const q = paletteSearch.value.trim().toLowerCase();
        paletteListEl.querySelectorAll('.wf-pal-group').forEach(group => {
            let anyVisible = false;
            group.querySelectorAll('.wf-pal-item').forEach(item => {
                if (item.classList.contains('wf-pal-special')) { anyVisible = true; return; }
                const hit = !q || (item.dataset.search || '').includes(q);
                item.style.display = hit ? '' : 'none';
                if (hit) anyVisible = true;
            });
            group.style.display = anyVisible ? '' : 'none';
        });
    });

    // ---- steps canvas ------------------------------------------------------
    function renderSteps() {
        const steps = state.def.steps || [];
        stepsEmpty.style.display = steps.length ? 'none' : '';
        stepsEl.innerHTML = steps.map((s, i) => stepCard(s, i)).join('');
        syncHighlights();
        initStepsSortable();
    }

    function stepCard(s, i) {
        const kind = stepKind(s);
        const icon = kind === 'tool' ? '🔧' : kind === 'prompt' ? '💬' : kind === 'speak' ? '🔊' : kind === 'shell' ? '🖥️' : kind === 'extract' ? '🔎' : kind === 'stop' ? '🛑' : kind === 'foreach' ? '🔁' : '🧩';
        const title = kind === 'tool' ? esc(s.tool) : kind === 'prompt' ? 'Prompt' : kind === 'speak' ? 'Speak' : kind === 'shell' ? 'Shell' : kind === 'extract' ? 'Extract' : kind === 'stop' ? 'Stop' : kind === 'foreach' ? 'Loop' : 'Workflow';
        return `<div class="wf-step wf-step-${kind}" data-uid="${s._uid}">
            <div class="wf-step-head">
                <span class="wf-drag" title="Drag to reorder">⠿</span>
                <span class="wf-step-num">#${i + 1}</span>
                <span class="wf-step-kind">${icon} ${title}</span>
                <input class="input-field wf-step-id" data-role="id" placeholder="id (optional)" value="${esc(s.id || '')}">
                <button class="action-btn delete" data-action="del-step" title="Remove step">×</button>
            </div>
            <div class="wf-step-body">${whenInput(s, kind)}${stepBody(s, kind)}</div>
        </div>`;
    }

    // Hover reference for the condition mini-language (used by `when` and Stop).
    const WHEN_TIP = 'Condition syntax (no LLM, case-insensitive):\n' +
        '{{var}} == value    {{var}} != value\n' +
        '{{var}} contains text    {{var}} not contains text\n' +
        '{{var}} is empty    {{var}} is not empty\n' +
        '{{var}} > number    {{var}} < number\n' +
        'Left/right sides can be {{vars}} or literals; quotes optional.\n' +
        'Examples: {{is_urgent}} == true · {{weather}} contains rain · {{inbox}} is empty';

    // Optional guard on any step (except Stop, which has its own condition):
    // the step runs only if the condition passes.
    function whenInput(s, kind) {
        if (kind === 'stop') return '';
        return `<input class="input-field wf-when" data-role="when"
            placeholder="when (optional) — run only if… e.g. {{is_urgent}} == true"
            title="${WHEN_TIP}"
            value="${esc(s.when || '')}">`;
    }

    function stepBody(s, kind) {
        if (kind === 'prompt') {
            return `<div class="wf-hl-wrap">
                <div class="wf-hl-back input-field wf-prompt" aria-hidden="true"></div>
                <textarea class="input-field wf-prompt wf-hl-input" data-role="prompt" rows="3"
                placeholder="Instruction. Reference context with {{step_id}}, {{param}}, {{today}}…">${esc(s.prompt || '')}</textarea>
                </div>
                ${modelInput(s)}`;
        }
        if (kind === 'speak') {
            return `<div class="wf-hl-wrap">
                <div class="wf-hl-back input-field wf-prompt" aria-hidden="true"></div>
                <textarea class="input-field wf-prompt wf-hl-input" data-role="speak" rows="2"
                placeholder="What to say aloud. Reference {{step_id}}, {{param}}, {{today}}…">${esc(s.speak || '')}</textarea>
                </div>`;
        }
        if (kind === 'shell') {
            return `<div class="wf-args">
                <div class="wf-shell-warn">⚠️ Unrestricted — runs any command on this machine as your user. No allow/deny list, no sandbox. Auto-triggering workflows (voice/schedule) run it with no confirmation.</div>
                <label class="wf-arg">
                    <span class="wf-arg-name">command</span>
                    <input class="input-field" data-role="shell-command"
                        placeholder="e.g. osascript -e 'display notification \"{{msg}}\"'"
                        value="${esc(s.shell.command || '')}">
                </label>
                <label class="wf-arg">
                    <span class="wf-arg-name">cwd (optional)</span>
                    <input class="input-field" data-role="shell-cwd"
                        placeholder="default: ~" value="${esc(s.shell.cwd || '')}">
                </label>
                <label class="wf-arg">
                    <span class="wf-arg-name">timeout seconds (optional)</span>
                    <input class="input-field" data-role="shell-timeout"
                        placeholder="default: 30, max: 120" value="${esc(s.shell.timeout || '')}">
                </label>
            </div>`;
        }
        if (kind === 'tool') {
            const info = state.toolIndex[s.tool];
            const keys = [];
            if (info) info.params.forEach(p => keys.push(p.name));
            Object.keys(s.args || {}).forEach(k => { if (!keys.includes(k)) keys.push(k); });
            if (!keys.length) return `<div class="wf-hint">This tool takes no arguments.</div>`;
            return `<div class="wf-args">` + keys.map(k => {
                const p = info && info.params.find(x => x.name === k);
                const hint = p ? (p.type + (p.required ? ' · required' : '')) : 'arg';
                return `<label class="wf-arg">
                    <span class="wf-arg-name">${esc(k)}${p && p.required ? ' *' : ''}</span>
                    <input class="input-field" data-role="arg" data-key="${esc(k)}"
                        placeholder="${esc(hint)}" value="${esc((s.args || {})[k] || '')}">
                    ${p && p.description ? `<span class="wf-arg-desc">${esc(p.description)}</span>` : ''}
                </label>`;
            }).join('') + `</div>`;
        }
        if (kind === 'stop') {
            return `<div class="wf-args">
                <label class="wf-arg" title="${WHEN_TIP}">
                    <span class="wf-arg-name">stop when ⓘ</span>
                    <input class="input-field" data-role="stop-when"
                        placeholder="e.g. {{today}} contains 'No events' — empty = always stop"
                        title="${WHEN_TIP}"
                        value="${esc(s.stop.when || '')}">
                </label>
                <label class="wf-arg">
                    <span class="wf-arg-name">output on stop</span>
                    <input class="input-field" data-role="stop-output"
                        placeholder="final output (optional) — e.g. Quiet morning, nothing on deck."
                        title="The workflow's final output when it stops here. Can reference {{vars}} — params, prior step ids, step1/step2…, extract fields, and built-ins (today, now, weekday…). Leave empty to return the previous step's output."
                        value="${esc(s.stop.output || '')}">
                </label>
            </div>`;
        }
        if (kind === 'extract') {
            const rows = (s.extract.fields || []).map((f, idx) => `
                <div class="wf-argrow" data-idx="${idx}">
                    <input class="input-field" data-role="ex-id" data-idx="${idx}" placeholder="variable id" value="${esc(f.id)}">
                    <input class="input-field" data-role="ex-desc" data-idx="${idx}" placeholder="what it should hold" value="${esc(f.description || '')}">
                    <button class="action-btn delete" data-action="ex-del" data-idx="${idx}">×</button>
                </div>`).join('');
            return `<div class="wf-extract">
                <label class="wf-arg">
                    <span class="wf-arg-name">input</span>
                    <input class="input-field" data-role="ex-input" placeholder="text to extract from, e.g. {{step1}}" value="${esc(s.extract.input || '')}">
                </label>
                <div class="wf-block-head"><span>Fields → variables</span></div>
                <div class="wf-argrows">${rows}</div>
                <button class="action-btn" data-action="ex-add">+ field</button>
                ${modelInput(s)}
            </div>`;
        }
        if (kind === 'foreach') {
            const asName = (s.foreach.as || '').trim() || 'item';
            return `<div class="wf-args">
                <label class="wf-arg">
                    <span class="wf-arg-name">items</span>
                    <input class="input-field" data-role="fe-items"
                        placeholder="what to loop over — {{step_id}}, a JSON array, or one item per line / comma-separated"
                        value="${esc(s.foreach.items || '')}">
                </label>
                <label class="wf-arg">
                    <span class="wf-arg-name">as (optional)</span>
                    <input class="input-field" data-role="fe-as"
                        placeholder="variable name per item — default: item" value="${esc(s.foreach.as || '')}">
                </label>
                <label class="wf-arg">
                    <span class="wf-arg-name">join (optional)</span>
                    <input class="input-field" data-role="fe-join"
                        placeholder="text between per-item outputs — default: one per line" value="${esc(s.foreach.join || '')}">
                </label>
                <div class="wf-block-head"><span>Steps per item (JSON list — same shapes as any step)</span></div>
                <textarea class="input-field wf-prompt wf-fe-steps" data-role="fe-steps" rows="6"
                    spellcheck="false">${esc(s._bodyText || '[]')}</textarea>
                <div class="wf-json-error wf-fe-err"></div>
                <div class="wf-hint">Inside the loop: {{${esc(asName)}}} = current item, {{loop_index}} (1-based), {{loop_total}}. A stop in here ends the whole workflow. Max 100 items.</div>
            </div>`;
        }

        // workflow node
        const opts = (state.palette.workflows || []).map(n =>
            `<option value="${esc(n)}" ${s.workflow === n ? 'selected' : ''}>${esc(n)}</option>`).join('');
        const argRows = (s._args || []).map((a, idx) => `
            <div class="wf-argrow" data-idx="${idx}">
                <input class="input-field" data-role="wf-argk" data-idx="${idx}" placeholder="arg" value="${esc(a.k)}">
                <input class="input-field" data-role="wf-argv" data-idx="${idx}" placeholder="value / {{ref}}" value="${esc(a.v)}">
                <button class="action-btn delete" data-action="del-arg" data-idx="${idx}">×</button>
            </div>`).join('');
        const toggle = s.workflow
            ? `<button class="action-btn" data-action="wf-toggle">${s._expanded ? '▾ hide steps' : '▸ view steps'}</button>`
            : '';
        return `<div class="wf-wf-node">
            <select class="input-field" data-role="wf-select">
                <option value="">— pick a workflow —</option>${opts}
            </select>
            <div class="wf-argrows">${argRows}</div>
            <div class="wf-node-actions">
                <button class="action-btn" data-action="add-arg">+ arg</button>
                ${toggle}
            </div>
            ${s._expanded && s.workflow ? wfPreview(s.workflow) : ''}
        </div>`;
    }

    // ---- read-only sub-workflow preview (inside a 🧩 node) -------------------
    function previewStepLine(st, i) {
        const kind = stepKind(st);
        const icon = { tool: '🔧', prompt: '💬', speak: '🔊', shell: '🖥️', extract: '🔎', stop: '🛑', foreach: '🔁', workflow: '🧩' }[kind];
        let detail = '';
        if (kind === 'tool') {
            const args = Object.entries(st.args || {}).map(([k, v]) => `${k}=${v}`).join(', ');
            detail = esc(st.tool) + (args ? ` (${esc(args)})` : '');
        } else if (kind === 'prompt') {
            const p = st.prompt || '';
            detail = '“' + esc(p.slice(0, 120)) + (p.length > 120 ? '…' : '') + '”' + (st.model ? ` <span class="wf-preview-meta">[${esc(st.model)}]</span>` : '');
        } else if (kind === 'speak') {
            const p = st.speak || '';
            detail = '“' + esc(p.slice(0, 120)) + (p.length > 120 ? '…' : '') + '”';
        } else if (kind === 'shell') {
            const sh = st.shell || {};
            detail = '<code>' + esc((sh.command || '').slice(0, 100)) + '</code>' + (sh.cwd ? ` <span class="wf-preview-meta">in ${esc(sh.cwd)}</span>` : '');
        } else if (kind === 'extract') {
            detail = `from ${esc((st.extract || {}).input || '')} → ${esc(((st.extract || {}).fields || []).map(f => f.id).join(', '))}`;
        } else if (kind === 'stop') {
            const sp = st.stop || {};
            detail = (sp.when ? `when ${esc(sp.when)}` : 'always') + (sp.output ? ` → “${esc(sp.output.slice(0, 60))}”` : '');
        } else if (kind === 'foreach') {
            const fe = st.foreach || {};
            detail = `${(fe.steps || []).length} step(s) per item of ${esc(fe.items || '')}` +
                (fe.as ? ` <span class="wf-preview-meta">as {{${esc(fe.as)}}}</span>` : '');
        } else {
            detail = esc(st.workflow || '');
        }
        const id = st.id ? ` <span class="wf-preview-id">{{${esc(st.id)}}}</span>` : '';
        const when = st.when ? ` <span class="wf-preview-when">when ${esc(st.when)}</span>` : '';
        return `<div class="wf-preview-step">#${i + 1} ${icon} ${detail}${id}${when}</div>`;
    }

    function wfPreview(name) {
        const def = state.wfDefs[name];
        if (!def || def.pending) return `<div class="wf-preview"><div class="wf-hint">loading ${esc(name)}…</div></div>`;
        if (def.error) return `<div class="wf-preview"><div class="wf-hint">couldn't load '${esc(name)}': ${esc(def.error)}</div></div>`;
        const params = (def.params || []).map(p => p.name).filter(Boolean).join(', ');
        return `<div class="wf-preview">
            <div class="wf-preview-head">${esc(def.name)} — ${esc(def.description || '')}</div>
            ${params ? `<div class="wf-preview-meta">params: ${esc(params)}</div>` : ''}
            ${(def.steps || []).map(previewStepLine).join('')}
            ${def.output ? `<div class="wf-preview-meta">output: ${esc(def.output)}</div>` : ''}
        </div>`;
    }

    async function loadWfDef(name) {
        state.wfDefs[name] = { pending: true };
        const def = await api('/api/workflows/' + encodeURIComponent(name));
        state.wfDefs[name] = def || { error: 'not reachable' };
        renderSteps();
    }

    function ensureWfDef(name) {
        if (name && !state.wfDefs[name]) loadWfDef(name);
    }

    function initStepsSortable() {
        if (state.stepsSortable) { try { state.stepsSortable.destroy(); } catch (e) {} }
        state.stepsSortable = new Sortable(stepsEl, {
            group: { name: 'wf', put: true },
            draggable: '.wf-step', handle: '.wf-drag', animation: 150,
            onAdd: onPaletteDrop, onUpdate: onReorder,
        });
    }

    function onPaletteDrop(evt) {
        const node = evt.item.dataset.node, full = evt.item.dataset.full, idx = evt.newIndex;
        // Defer: let Sortable finish, then swap the dropped clone for a real model step.
        setTimeout(() => {
            if (evt.item.parentNode) evt.item.parentNode.removeChild(evt.item);
            let step;
            if (node === 'tool') step = { tool: full, args: {}, id: '', _uid: uid() };
            else if (node === 'prompt') step = { prompt: '', id: '', _uid: uid() };
            else if (node === 'speak') step = { speak: '', id: '', _uid: uid() };
            else if (node === 'shell') step = { shell: { command: '', cwd: '', timeout: '' }, id: '', _uid: uid() };
            else if (node === 'extract') step = { extract: { input: '', fields: [] }, id: '', _uid: uid() };
            else if (node === 'stop') step = { stop: { when: '', output: '' }, id: '', _uid: uid() };
            else if (node === 'foreach') step = { foreach: { items: '', as: '', join: '', steps: [] }, _bodyText: '[]', id: '', _uid: uid() };
            else step = { workflow: '', _args: [], id: '', _uid: uid() };
            state.def.steps.splice(idx, 0, step);
            renderSteps();
        }, 0);
    }

    function onReorder() {
        const order = [...stepsEl.querySelectorAll('.wf-step')].map(e => e.dataset.uid);
        state.def.steps.sort((a, b) => order.indexOf(a._uid) - order.indexOf(b._uid));
        setTimeout(renderSteps, 0); // refresh #N labels
    }

    // step-body edits via delegation (stepsEl persists across renders)
    stepsEl.addEventListener('input', (e) => {
        const card = e.target.closest('.wf-step'); if (!card) return;
        const s = stepByUid(card.dataset.uid); if (!s) return;
        const role = e.target.dataset.role;
        if (role === 'id') s.id = e.target.value;
        else if (role === 'prompt' || role === 'speak') {
            s[role] = e.target.value;
            const back = e.target.closest('.wf-hl-wrap')?.querySelector('.wf-hl-back');
            if (back) back.innerHTML = hlHTML(e.target.value);
        }
        else if (role === 'arg') s.args[e.target.dataset.key] = e.target.value;
        else if (role === 'wf-argk') s._args[+e.target.dataset.idx].k = e.target.value;
        else if (role === 'wf-argv') s._args[+e.target.dataset.idx].v = e.target.value;
        else if (role === 'ex-input') s.extract.input = e.target.value;
        else if (role === 'ex-id') s.extract.fields[+e.target.dataset.idx].id = e.target.value;
        else if (role === 'ex-desc') s.extract.fields[+e.target.dataset.idx].description = e.target.value;
        else if (role === 'model') s.model = e.target.value;
        else if (role === 'when') s.when = e.target.value;
        else if (role === 'stop-when') s.stop.when = e.target.value;
        else if (role === 'stop-output') s.stop.output = e.target.value;
        else if (role === 'shell-command') s.shell.command = e.target.value;
        else if (role === 'shell-cwd') s.shell.cwd = e.target.value;
        else if (role === 'shell-timeout') s.shell.timeout = e.target.value;
        else if (role === 'fe-items') s.foreach.items = e.target.value;
        else if (role === 'fe-as') s.foreach.as = e.target.value;
        else if (role === 'fe-join') s.foreach.join = e.target.value;
        else if (role === 'fe-steps') {
            // Keep the text as typed; only adopt it into the model when it parses.
            // buildDef() serializes the last valid parse, so a half-edited body
            // can't corrupt the definition — the error line shows why.
            s._bodyText = e.target.value;
            const err = card.querySelector('.wf-fe-err');
            try {
                const parsed = JSON.parse(e.target.value);
                if (!Array.isArray(parsed)) throw new Error('must be a JSON list of steps');
                s.foreach.steps = parsed;
                if (err) err.textContent = '';
            } catch (ex) {
                if (err) err.textContent = 'Not saved yet — ' + ex.message;
            }
        }
    });
    stepsEl.addEventListener('change', (e) => {
        if (e.target.dataset.role === 'wf-select') {
            const card = e.target.closest('.wf-step');
            const s = stepByUid(card.dataset.uid);
            s.workflow = e.target.value;
            if (s._expanded) ensureWfDef(s.workflow);
            renderSteps(); // refresh the toggle/preview for the new selection
        }
    });
    stepsEl.addEventListener('click', (e) => {
        const card = e.target.closest('.wf-step'); if (!card) return;
        const s = stepByUid(card.dataset.uid); const act = e.target.dataset.action;
        if (act === 'del-step') { state.def.steps = state.def.steps.filter(x => x._uid !== s._uid); renderSteps(); }
        else if (act === 'add-arg') { s._args.push({ k: '', v: '' }); renderSteps(); }
        else if (act === 'del-arg') { s._args.splice(+e.target.dataset.idx, 1); renderSteps(); }
        else if (act === 'ex-add') { s.extract.fields.push({ id: '', description: '' }); renderSteps(); }
        else if (act === 'ex-del') { s.extract.fields.splice(+e.target.dataset.idx, 1); renderSteps(); }
        else if (act === 'wf-toggle') {
            s._expanded = !s._expanded;
            if (s._expanded) ensureWfDef(s.workflow);
            renderSteps();
        }
    });

    // ---- serialize ---------------------------------------------------------
    function cleanArgs(obj) {
        const o = {};
        Object.entries(obj || {}).forEach(([k, v]) => { if (k && v !== '' && v != null) o[k] = v; });
        return o;
    }
    function argsFromRows(rows) {
        const o = {};
        (rows || []).forEach(({ k, v }) => { if (k && k.trim()) o[k.trim()] = v; });
        return o;
    }
    function buildDef() {
        const d = {
            name: (state.def.name || '').trim(),
            description: (state.def.description || '').trim(),
            params: (state.def.params || []).filter(p => (p.name || '').trim()).map(p => {
                const o = { name: p.name.trim() };
                if (p.required) o.required = true;
                if (p.default !== '' && p.default != null) o.default = p.default;
                if (p.description) o.description = p.description;
                return o;
            }),
            steps: (state.def.steps || []).map(s => {
                const o = {};
                if ((s.id || '').trim()) o.id = s.id.trim();
                const kind = stepKind(s);
                if (kind === 'tool') { o.tool = s.tool; const a = cleanArgs(s.args); if (Object.keys(a).length) o.args = a; }
                else if (kind === 'prompt') { o.prompt = s.prompt || ''; }
                else if (kind === 'speak') { o.speak = s.speak || ''; }
                else if (kind === 'shell') {
                    o.shell = { command: s.shell.command || '' };
                    if ((s.shell.cwd || '').trim()) o.shell.cwd = s.shell.cwd.trim();
                    const to = parseFloat(s.shell.timeout);
                    if (!isNaN(to) && to > 0) o.shell.timeout = to;
                }
                else if (kind === 'extract') {
                    o.extract = {
                        input: s.extract.input || '',
                        fields: (s.extract.fields || []).filter(f => (f.id || '').trim())
                            .map(f => ({ id: f.id.trim(), description: f.description || '' })),
                    };
                }
                else if (kind === 'stop') {
                    o.stop = {};
                    if ((s.stop.when || '').trim()) o.stop.when = s.stop.when.trim();
                    if ((s.stop.output || '').trim()) o.stop.output = s.stop.output.trim();
                }
                else if (kind === 'foreach') {
                    o.foreach = { items: s.foreach.items || '', steps: s.foreach.steps || [] };
                    if ((s.foreach.as || '').trim()) o.foreach.as = s.foreach.as.trim();
                    if (s.foreach.join) o.foreach.join = s.foreach.join;
                }
                else { o.workflow = s.workflow || ''; const a = argsFromRows(s._args); if (Object.keys(a).length) o.args = a; }
                if ((kind === 'prompt' || kind === 'extract') && (s.model || '').trim()) o.model = s.model.trim();
                if (kind !== 'stop' && (s.when || '').trim()) o.when = s.when.trim();
                return o;
            }),
            surfaces: {
                schedulable: !!state.def.surfaces.schedulable,
                expose_as_tool: !!state.def.surfaces.expose_as_tool,
            },
        };
        const out = (state.def.output || '').trim();
        if (out) d.output = out;
        const trigs = (state.def.triggers || []).map(t => t.trim()).filter(Boolean);
        if (trigs.length) d.triggers = trigs; // empty => backend auto-generates
        return d;
    }

    // ---- save --------------------------------------------------------------
    async function saveWorkflow() {
        const def = buildDef();
        const res = await api('/api/workflows', { method: 'POST', body: JSON.stringify(def) });
        if (!res) return;
        if (res.error) { showSaveMsg(res.error, true); return; }
        showSaveMsg(`Saved (${res.action}).`, false);
        editorTitle.textContent = def.name;
        setTimeout(() => { showList(); loadWorkflows(); }, 500);
    }
    function showSaveMsg(text, isError) {
        saveMsg.textContent = text;
        saveMsg.className = 'wf-save-msg ' + (isError ? 'error' : 'ok');
        saveMsg.style.display = '';
    }

    // ---- test --------------------------------------------------------------
    document.getElementById('wf-test-close').addEventListener('click', () => testPanel.style.display = 'none');
    document.getElementById('wf-test-run').addEventListener('click', runTest);

    function openTestPanel() {
        const def = buildDef();
        testPanel.style.display = '';
        testResult.innerHTML = '';
        const ps = def.params || [];
        if (ps.length) {
            testParams.innerHTML = '<div class="wf-hint">Parameter values for this run:</div>' + ps.map(p => `
                <label class="wf-arg">
                    <span class="wf-arg-name">${esc(p.name)}${p.required ? ' *' : ''}</span>
                    <input class="input-field" data-tparam="${esc(p.name)}" value="${esc(p.default || '')}">
                </label>`).join('');
            testRunRow.style.display = '';
        } else {
            testParams.innerHTML = '';
            testRunRow.style.display = 'none';
            runTest();
        }
    }

    async function runTest() {
        const params = {};
        testParams.querySelectorAll('[data-tparam]').forEach(i => { params[i.dataset.tparam] = i.value; });
        testResult.innerHTML = '<div class="wf-hint" id="wf-test-progress">Starting… (tools run for real; LLM steps can take up to a minute)</div>';
        clearStepHighlights();
        let res;
        try {
            res = await fetch('/api/workflows/test', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ definition: buildDef(), params }),
            });
        } catch (e) {
            testResult.innerHTML = `<div class="wf-save-msg error" style="display:block">${esc(e.message)}</div>`;
            return;
        }
        if (res.status === 401) { location.href = '/login'; return; }

        // Read the SSE stream: "start" events update the progress line + highlight
        // the running card; the final "result" event renders output + trace.
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buf += decoder.decode(value, { stream: true });
            let idx;
            while ((idx = buf.indexOf('\n\n')) >= 0) {
                const line = buf.slice(0, idx).replace(/^data: ?/, '').trim();
                buf = buf.slice(idx + 2);
                if (!line) continue;
                let ev; try { ev = JSON.parse(line); } catch { continue; }
                handleTestEvent(ev);
            }
        }
        clearStepHighlights();
    }

    function handleTestEvent(ev) {
        if (ev.type === 'start') {
            const prog = document.getElementById('wf-test-progress');
            const where = ev.depth > 0 ? ' · in sub-workflow' : '';
            if (prog) prog.textContent = `Running step ${ev.index}: ${ev.label}${where}…`;
            if (ev.depth === 0) highlightStep(ev.index);
        } else if (ev.type === 'skip') {
            const prog = document.getElementById('wf-test-progress');
            if (prog) prog.textContent = `Skipped step ${ev.index}: ${ev.label} (when false)`;
        } else if (ev.type === 'result') {
            renderTestResult(ev);
        }
    }

    function highlightStep(index) {
        clearStepHighlights();
        const card = stepsEl.querySelectorAll('.wf-step')[index - 1];
        if (card) card.classList.add('wf-step-running');
    }
    function clearStepHighlights() {
        stepsEl.querySelectorAll('.wf-step-running').forEach(c => c.classList.remove('wf-step-running'));
    }

    function renderTestResult(res) {
        let html = '';
        if (res.error) html += `<div class="wf-save-msg error" style="display:block">${esc(res.error)}</div>`;
        const trace = res.trace || [];
        if (trace.length) {
            html += '<div class="wf-trace">' + trace.map((t, i) => `
                <div class="wf-trace-step">
                    <div class="wf-trace-head">#${i + 1} · ${esc(t.kind)} · <b>${esc(t.step)}</b></div>
                    <pre class="wf-trace-out">${esc(t.output)}</pre>
                </div>`).join('') + '</div>';
        }
        if (res.output != null && !res.error) {
            html += `<div class="wf-block-head"><span>Output</span></div><pre class="wf-output">${esc(res.output)}</pre>`;
        }
        testResult.innerHTML = html || '<div class="wf-hint">No output.</div>';
    }

    // ---- {{variable}} highlighting -----------------------------------------
    // A textarea can't color its own text, so a backdrop div (same metrics, same
    // grid cell) renders the text with {{vars}} wrapped in colored spans while the
    // textarea's own text is transparent. Kept in sync on input + scroll.
    function hlHTML(text) {
        return esc(text).replace(/\{\{\s*[A-Za-z0-9_]+\s*\}\}/g,
            m => `<span class="wf-var">${m}</span>`) + '\n';
    }
    function syncHighlights() {
        stepsEl.querySelectorAll('.wf-hl-wrap').forEach(w => {
            const ta = w.querySelector('textarea');
            const back = w.querySelector('.wf-hl-back');
            if (ta && back) back.innerHTML = hlHTML(ta.value);
        });
    }
    stepsEl.addEventListener('scroll', (e) => {
        if (e.target.classList && e.target.classList.contains('wf-hl-input')) {
            const back = e.target.closest('.wf-hl-wrap').querySelector('.wf-hl-back');
            back.scrollTop = e.target.scrollTop;
            back.scrollLeft = e.target.scrollLeft;
        }
    }, true);

    // ---- {{ autocomplete -----------------------------------------------------
    // Typing "{{" in any var-accepting field pops a dropdown of what's actually
    // in scope at that step: prior step ids/stepN, extract field ids, params,
    // and built-ins. Arrows + Enter/Tab accept; Escape closes.
    const AC_BUILTINS = ['today', 'yesterday', 'tomorrow', 'now', 'time', 'weekday'];
    let ac = { el: null, items: [], sel: 0, start: 0 };
    const acBox = document.createElement('div');
    acBox.id = 'wf-ac';
    acBox.style.display = 'none';
    document.body.appendChild(acBox);

    function isVarField(el) {
        if (!el || !el.matches) return false;
        if (el === elOutput) return true;
        return el.matches('#wf-editor-view [data-role="prompt"], #wf-editor-view [data-role="speak"], ' +
                          '#wf-editor-view [data-role="ex-input"], ' +
                          '#wf-editor-view [data-role="arg"], #wf-editor-view [data-role="wf-argv"], ' +
                          '#wf-editor-view [data-role="when"], #wf-editor-view [data-role="stop-when"], ' +
                          '#wf-editor-view [data-role="stop-output"], ' +
                          '#wf-editor-view [data-role="shell-command"], #wf-editor-view [data-role="shell-cwd"], ' +
                          '#wf-editor-view [data-role="fe-items"]');
    }

    function acVars(el) {
        const steps = state.def ? (state.def.steps || []) : [];
        const params = state.def ? (state.def.params || []).map(p => (p.name || '').trim()).filter(Boolean) : [];
        const card = el.closest ? el.closest('.wf-step') : null;
        let upto = steps.length; // output field: everything is in scope
        if (card) {
            const i = steps.findIndex(x => x._uid === card.dataset.uid);
            if (i >= 0) upto = i; // in a step: only PRIOR steps are in scope
        }
        const vars = [];
        for (let j = 0; j < upto; j++) {
            const st = steps[j];
            if ((st.id || '').trim()) vars.push(st.id.trim());
            vars.push('step' + (j + 1));
            if (st.extract) (st.extract.fields || []).forEach(f => {
                if ((f.id || '').trim()) vars.push(f.id.trim());
            });
        }
        return [...new Set([...vars, ...params, ...AC_BUILTINS])];
    }

    function acCheck(el) {
        const pos = el.selectionStart ?? el.value.length;
        const m = el.value.slice(0, pos).match(/\{\{\s*([A-Za-z0-9_]*)$/);
        if (!m) { hideAC(); return; }
        const partial = m[1];
        const items = acVars(el).filter(v => v.toLowerCase().startsWith(partial.toLowerCase()) && v !== partial);
        if (!items.length) { hideAC(); return; }
        ac = { el, items: items.slice(0, 12), sel: 0, start: pos - partial.length };
        acRender();
        const r = el.getBoundingClientRect();
        acBox.style.left = Math.round(r.left) + 'px';
        acBox.style.top = Math.round(Math.min(r.bottom, window.innerHeight - 220) + 2) + 'px';
        acBox.style.display = '';
    }

    function acRender() {
        acBox.innerHTML = ac.items.map((v, i) =>
            `<div class="wf-ac-item${i === ac.sel ? ' sel' : ''}" data-i="${i}">${esc(v)}</div>`).join('');
        const sel = acBox.querySelector('.sel');
        if (sel && sel.scrollIntoView) sel.scrollIntoView({ block: 'nearest' });
    }

    function acInsert(i) {
        const { el, items, start } = ac;
        const v = items[i];
        if (!el || v == null) return;
        const pos = el.selectionStart;
        const close = el.value.slice(pos).startsWith('}}') ? '' : '}}';
        el.value = el.value.slice(0, start) + v + close + el.value.slice(pos);
        const caret = start + v.length + 2;
        hideAC();
        el.focus();
        el.setSelectionRange(caret, caret);
        el.dispatchEvent(new Event('input', { bubbles: true })); // sync state + highlight
    }

    function hideAC() { acBox.style.display = 'none'; ac.el = null; }

    document.addEventListener('input', (e) => { if (isVarField(e.target)) acCheck(e.target); }, true);
    document.addEventListener('keydown', (e) => {
        if (acBox.style.display === 'none' || e.target !== ac.el) return;
        if (e.key === 'ArrowDown') { e.preventDefault(); ac.sel = (ac.sel + 1) % ac.items.length; acRender(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); ac.sel = (ac.sel - 1 + ac.items.length) % ac.items.length; acRender(); }
        else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); acInsert(ac.sel); }
        else if (e.key === 'Escape') { hideAC(); }
    }, true);
    document.addEventListener('focusin', (e) => { if (ac.el && e.target !== ac.el) hideAC(); });
    document.addEventListener('click', (e) => { if (!acBox.contains(e.target)) hideAC(); });
    acBox.addEventListener('mousedown', (e) => {
        const it = e.target.closest('.wf-ac-item');
        if (it) { e.preventDefault(); acInsert(+it.dataset.i); }
    });

    // ---- raw JSON ----------------------------------------------------------
    document.getElementById('wf-json-cancel').addEventListener('click', () => jsonModal.style.display = 'none');
    document.getElementById('wf-json-apply').addEventListener('click', applyJson);

    function openJson() {
        jsonError.textContent = '';
        jsonText.value = JSON.stringify(buildDef(), null, 2);
        jsonModal.style.display = '';
    }
    function applyJson() {
        let parsed;
        try { parsed = JSON.parse(jsonText.value); }
        catch (e) { jsonError.textContent = 'Invalid JSON: ' + e.message; return; }
        if (typeof parsed !== 'object' || Array.isArray(parsed)) { jsonError.textContent = 'Must be a JSON object.'; return; }
        state.def = parsed;
        normalizeDef(state.def);
        fillMeta();
        renderParams();
        renderSteps();
        jsonModal.style.display = 'none';
    }
})();
