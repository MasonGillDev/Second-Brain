/* Chat interface with image support */
(function() {
    const messages = document.getElementById('chat-messages');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    const cancelBtn = document.getElementById('chat-cancel');
    const statusDot = document.getElementById('chat-status');
    const statusLabel = document.getElementById('chat-status-label');
    let processing = false;
    let pendingImages = []; // {data: base64, media_type: string, preview: dataURL}
    const debugToggle = document.getElementById('chat-debug-toggle');

    function addMsg(cls, html) {
        const div = document.createElement('div');
        div.className = 'chat-msg ' + cls;
        div.innerHTML = html;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
        return div;
    }

    function addToolCall(name, args) {
        const div = document.createElement('div');
        div.className = 'chat-tool-call';
        const argsStr = typeof args === 'object' ? JSON.stringify(args) : String(args);
        div.innerHTML = `<div class="tool-name">${esc(name)}</div><div class="tool-args">${esc(argsStr).substring(0, 200)}</div>`;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function addDebugContext(systemPrompt, msgs) {
        const div = document.createElement('div');
        div.className = 'chat-debug-context';
        let msgsHtml = msgs.map(m => `<strong>${esc(m.role)}:</strong> ${esc(typeof m.content === 'string' ? m.content : JSON.stringify(m.content)).substring(0, 500)}`).join('<br><br>');
        div.innerHTML = `<details><summary>Full Prompt Sent to Model</summary><div class="debug-section"><h4>System Prompt</h4><pre>${esc(systemPrompt)}</pre></div><div class="debug-section"><h4>Messages</h4><div>${msgsHtml}</div></div></details>`;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function setStatus(state, text) {
        statusDot.className = 'status-dot' + (state !== 'connected' ? ' ' + state : '');
        statusLabel.textContent = text;
    }

    const ws = window.createWS('/ws/chat',
        (data) => {
            if (data.type === 'tool_call') {
                addToolCall(data.name, data.args);
            } else if (data.type === 'debug_context') {
                addDebugContext(data.system_prompt, data.messages);
            } else if (data.type === 'response') {
                addMsg('assistant', marked.parse(data.text || ''));
                setProcessing(false);
            } else if (data.type === 'error') {
                addMsg('assistant', '<span style="color:var(--red)">' + esc(data.text) + '</span>');
                setProcessing(false);
            } else if (data.type === 'cancelled') {
                addMsg('assistant', '<em style="color:var(--text-dim)">Cancelled.</em>');
                setProcessing(false);
            } else if (data.type === 'status') {
                setStatus('working', data.text);
            }
        },
        () => setStatus('connected', 'Connected'),
        () => setStatus('disconnected', 'Disconnected'),
    );

    function setProcessing(v) {
        processing = v;
        sendBtn.disabled = v;
        cancelBtn.style.display = v ? '' : 'none';
        if (!v) setStatus('connected', 'Connected');
    }

    function send() {
        const text = input.value.trim();
        if ((!text && pendingImages.length === 0) || processing) return;

        // Build user message HTML with image previews
        let msgHtml = '';
        if (pendingImages.length > 0) {
            msgHtml += '<div class="chat-images">';
            pendingImages.forEach(img => {
                msgHtml += `<img src="${img.preview}" class="chat-img-preview">`;
            });
            msgHtml += '</div>';
        }
        if (text) msgHtml += esc(text);
        addMsg('user', msgHtml);

        // Send with images
        const payload = { type: 'message', text, debug: debugToggle.checked };
        if (pendingImages.length > 0) {
            payload.images = pendingImages.map(img => ({
                data: img.data,
                media_type: img.media_type,
            }));
        }
        ws.send(payload);

        input.value = '';
        input.style.height = 'auto';
        clearPendingImages();
        setProcessing(true);
    }

    function clearPendingImages() {
        pendingImages = [];
        const preview = document.getElementById('image-preview');
        if (preview) preview.innerHTML = '';
        updateImagePreview();
    }

    function updateImagePreview() {
        let preview = document.getElementById('image-preview');
        if (!preview) {
            preview = document.createElement('div');
            preview.id = 'image-preview';
            preview.className = 'image-preview-bar';
            input.parentElement.insertBefore(preview, input);
        }
        if (pendingImages.length === 0) {
            preview.style.display = 'none';
            return;
        }
        preview.style.display = 'flex';
        preview.innerHTML = pendingImages.map((img, i) =>
            `<div class="image-preview-item">
                <img src="${img.preview}">
                <button class="image-preview-remove" onclick="window._removeImage(${i})">x</button>
            </div>`
        ).join('');
    }

    window._removeImage = function(idx) {
        pendingImages.splice(idx, 1);
        updateImagePreview();
    };

    function addImageFromFile(file) {
        if (!file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            const dataUrl = e.target.result;
            // Extract base64 data (remove "data:image/png;base64," prefix)
            const base64 = dataUrl.split(',')[1];
            const mediaType = file.type;
            pendingImages.push({
                data: base64,
                media_type: mediaType,
                preview: dataUrl,
            });
            updateImagePreview();
        };
        reader.readAsDataURL(file);
    }

    // Paste image from clipboard
    input.addEventListener('paste', (e) => {
        const items = e.clipboardData?.items;
        if (!items) return;
        for (const item of items) {
            if (item.type.startsWith('image/')) {
                e.preventDefault();
                addImageFromFile(item.getAsFile());
                return;
            }
        }
    });

    // Drag and drop
    const chatArea = document.querySelector('.chat-input-area');
    chatArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        chatArea.style.borderColor = 'var(--accent)';
    });
    chatArea.addEventListener('dragleave', () => {
        chatArea.style.borderColor = '';
    });
    chatArea.addEventListener('drop', (e) => {
        e.preventDefault();
        chatArea.style.borderColor = '';
        for (const file of e.dataTransfer.files) {
            addImageFromFile(file);
        }
    });

    sendBtn.addEventListener('click', send);
    cancelBtn.addEventListener('click', () => ws.send({ type: 'cancel' }));

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    });

    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });
})();
