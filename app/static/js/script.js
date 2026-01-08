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

    // ============================================
    // NUEVA FUNCIÓN: Validación de archivos
    // ============================================
    function validateFile(file) {
        // Formatos permitidos - ACTUALIZADO
        const validExtensions = ['.pdf', '.txt', '.md', '.epub', '.xlsx', '.xls'];
        const maxSizeBytes = 35 * 1024 * 1024; // 35 MB

        // Obtener extensión del archivo
        const fileName = file.name.toLowerCase();
        const fileExtension = fileName.substring(fileName.lastIndexOf('.'));

        // Validar extensión
        if (!validExtensions.includes(fileExtension)) {
            uploadStatus.textContent = `Formato no válido. Solo se aceptan: ${validExtensions.join(', ')}`;
            uploadStatus.className = "status-msg status-error";
            return false;
        }

        // Validar tamaño
        if (file.size > maxSizeBytes) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            uploadStatus.textContent = `Archivo muy grande (${sizeMB} MB). Máximo permitido: 35 MB`;
            uploadStatus.className = "status-msg status-error";
            return false;
        }

        // Validar que no esté vacío
        if (file.size === 0) {
            uploadStatus.textContent = "El archivo está vacío";
            uploadStatus.className = "status-msg status-error";
            return false;
        }

        return true;
    }

    async function handleUpload(file) {
        // ============================================
        // VALIDAR ANTES DE SUBIR
        // ============================================
        if (!validateFile(file)) {
            return; // Si no es válido, detener aquí
        }

        uploadStatus.textContent = `Subiendo ${file.name}...`;
        uploadStatus.className = "status-msg";

        // Indicador visual de que está cargando
        dropZone.style.opacity = '0.5';
        dropZone.style.pointerEvents = 'none';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/v1/documents/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                uploadStatus.textContent = `${file.name} subido con éxito`;
                uploadStatus.classList.add('status-success');
                updateStats();

                // Limpiar mensaje después de 3 segundos
                setTimeout(() => {
                    uploadStatus.textContent = "";
                    uploadStatus.className = "status-msg";
                }, 3000);
            } else {
                uploadStatus.textContent = "Error: " + data.detail;
                uploadStatus.classList.add('status-error');
            }
        } catch (err) {
            uploadStatus.textContent = "Error de conexión con el servidor";
            uploadStatus.classList.add('status-error');
        } finally {
            // Restaurar estado del drop zone
            dropZone.style.opacity = '1';
            dropZone.style.pointerEvents = 'auto';
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
