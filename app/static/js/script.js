document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const docCountEl = document.getElementById('doc-count');
    const modelNameEl = document.getElementById('model-name');
    const maxResultsInput = document.getElementById('max-results');

    // Initial stats load
    updateStats();
    setInterval(updateStats, 10000);

    // File Upload handling
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('active');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('active');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('active');
        const file = e.dataTransfer.files[0];
        if (file) handleUpload(file);
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) handleUpload(fileInput.files[0]);
    });

    async function handleUpload(file) {
        uploadStatus.textContent = "Subiendo...";
        uploadStatus.className = "status-msg";

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/v1/documents/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                uploadStatus.textContent = "¡Subido con éxito!";
                uploadStatus.classList.add('status-success');
                updateStats();
            } else {
                uploadStatus.textContent = "Error: " + data.detail;
                uploadStatus.classList.add('status-error');
            }
        } catch (err) {
            uploadStatus.textContent = "Error de conexión";
            uploadStatus.classList.add('status-error');
        }
    }

    // Chat handling
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        appendMessage('user', text);
        userInput.value = '';

        const loadingMsg = appendMessage('ai', 'Pensando...');

        try {
            const response = await fetch('/api/v1/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: text,
                    max_results: parseInt(maxResultsInput.value)
                })
            });

            const data = await response.json();
            chatMessages.removeChild(loadingMsg);

            if (response.ok) {
                appendMessage('ai', data.answer, data.sources);
            } else {
                appendMessage('ai', "Lo siento, hubo un error: " + data.detail);
            }
        } catch (err) {
            chatMessages.removeChild(loadingMsg);
            appendMessage('ai', "Error de conexión con el servidor.");
        }
    }

    function appendMessage(sender, text, sources = []) {
        const msgDiv = document.createElement('div');
        msgDiv.className = sender === 'user' ? 'user-message' : 'ai-message';

        let content = text;
        if (sources && sources.length > 0) {
            content += '<div class="sources-title">Fuentes consultadas:</div>';
            sources.forEach(src => {
                content += `<div class="source-tag">${src.metadata.filename || 'Doc'} (Relevancia: ${(src.relevance_score * 100).toFixed(1)}%)</div>`;
            });
        }

        msgDiv.innerHTML = content;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    }

    async function updateStats() {
        try {
            const response = await fetch('/api/v1/stats');
            const data = await response.json();
            docCountEl.textContent = data.total_documents;
            modelNameEl.textContent = data.model;
        } catch (err) {
            console.error("Error updating stats", err);
        }
    }
});
