document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');
    const docCount = document.getElementById('doc-count');
    const modelName = document.getElementById('model-name');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const maxResultsSlider = document.getElementById('max-results');
    const maxResultsVal = document.getElementById('max-results-val');

    // Upload Metadata Inputs
    const uploadTags = document.getElementById('upload-tags');
    const uploadDesc = document.getElementById('upload-desc');

    // Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    // Document Management
    const docListContainer = document.getElementById('documents-list-container');
    const refreshDocsBtn = document.getElementById('refresh-docs');
    const docSearchInput = document.getElementById('doc-search');

    // Modal Elements
    const modal = document.getElementById('doc-modal');
    const closeModal = document.querySelector('.close-modal');
    const modalFilename = document.getElementById('modal-filename');
    const modalType = document.getElementById('modal-type');
    const modalId = document.getElementById('modal-id');
    const modalDate = document.getElementById('modal-date');
    const modalSize = document.getElementById('modal-size');
    const modalChunks = document.getElementById('modal-chunks');
    const modalTags = document.getElementById('modal-tags');
    const modalDesc = document.getElementById('modal-desc');
    const saveMetaBtn = document.getElementById('save-meta-btn');
    const deleteDocBtn = document.getElementById('delete-doc-btn');
    const genSummaryBtn = document.getElementById('gen-summary-btn');
    const summaryResult = document.getElementById('summary-result');

    // State
    let currentDocId = null;
    let allDocuments = [];

    // --- Initialization ---
    fetchStats();

    // --- Tab Switching ---
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active to clicked
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');

            // If switching to documents tab, load documents
            if (tabId === 'documents-tab') {
                loadDocuments();
            }
        });
    });

    // --- Slider ---
    if (maxResultsSlider) {
        maxResultsSlider.addEventListener('input', (e) => {
            maxResultsVal.textContent = e.target.value;
        });
    }

    // --- File Upload ---
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleUpload(fileInput.files[0]);
        }
    });

    async function handleUpload(file) {
        const formData = new FormData();
        formData.append('file', file);

        // Append metadata if present
        if (uploadTags && uploadTags.value) {
            formData.append('tags', uploadTags.value);
        }
        if (uploadDesc && uploadDesc.value) {
            formData.append('description', uploadDesc.value);
        }

        showStatus('Subiendo...', 'info');

        try {
            const response = await fetch('/api/v1/documents/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Error al subir archivo');
            }

            const data = await response.json();
            showStatus(`¡Éxito! ${data.filename} procesado (${data.chunks_created} chunks)`, 'success');
            fetchStats();

            // Clear inputs
            fileInput.value = '';
            uploadTags.value = '';
            uploadDesc.value = '';

            // Refresh list if we are on that tab (though we are on upload tab usually)
            // loadDocuments(); 
        } catch (error) {
            showStatus(error.message, 'error');
        }
    }

    function showStatus(msg, type) {
        uploadStatus.textContent = msg;
        uploadStatus.className = 'status-msg ' + type;
        uploadStatus.style.display = 'block';
    }

    // --- Chat ---
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // Add user message
        addMessage(text, 'user');
        userInput.value = '';

        // Show loading
        const loadingId = addMessage('Pensando...', 'ai', true);

        try {
            const response = await fetch('/api/v1/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: text,
                    max_results: parseInt(maxResultsSlider.value)
                })
            });

            const data = await response.json();

            // Remove loading
            document.getElementById(loadingId).remove();

            if (!response.ok) {
                addMessage(`Error: ${data.detail}`, 'ai');
            } else {
                let aiText = data.answer;
                // Add sources if available
                if (data.sources && data.sources.length > 0) {
                    aiText += "\n\n**Fuentes:**\n";
                    data.sources.forEach(src => {
                        const filename = src.metadata.filename || 'Desconocido';
                        aiText += `- ${filename} (Score: ${src.relevance_score.toFixed(2)})\n`;
                    });
                }
                addMessage(aiText, 'ai');
            }

        } catch (error) {
            document.getElementById(loadingId).remove();
            addMessage('Error de conexión con el servidor', 'ai');
        }
    }

    function addMessage(text, type, isLoading = false) {
        const div = document.createElement('div');
        div.className = `${type}-message`;
        if (isLoading) div.id = 'loading-' + Date.now();

        let content = text;
        if (type === 'ai' && !isLoading) {
            // Render markdown using marked
            // Simple clean up mostly
            content = marked.parse(text);
        }

        const icon = type === 'ai' ? '<div class="message-icon"><i class="fas fa-robot"></i></div>' : '';

        div.innerHTML = `
            ${icon}
            <div class="message-content">${content}</div>
        `;

        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return div.id;
    }

    // --- Document Management ---

    refreshDocsBtn.addEventListener('click', loadDocuments);

    // Search filtering
    docSearchInput.addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allDocuments.filter(doc =>
            (doc.filename && doc.filename.toLowerCase().includes(term)) ||
            (doc.tags && doc.tags.some(tag => tag.toLowerCase().includes(term)))
        );
        renderDocuments(filtered);
    });

    async function loadDocuments() {
        docListContainer.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Cargando...</div>';
        try {
            const response = await fetch('/api/v1/documents');
            const data = await response.json();

            if (response.ok) {
                allDocuments = data.documents;
                renderDocuments(allDocuments);
            } else {
                docListContainer.innerHTML = '<div class="loading-state">Error al cargar documentos</div>';
            }
        } catch (error) {
            docListContainer.innerHTML = `<div class="loading-state">Error: ${error.message}</div>`;
        }
    }

    function renderDocuments(docs) {
        docListContainer.innerHTML = '';

        if (docs.length === 0) {
            docListContainer.innerHTML = '<div class="loading-state">No se encontraron documentos.</div>';
            return;
        }

        docs.forEach(doc => {
            const card = document.createElement('div');
            card.className = 'doc-card';
            card.onclick = () => openModal(doc.document_id);

            // Determine icon
            let iconClass = 'fa-file-alt txt';
            const ext = doc.file_type || '';
            if (ext.includes('pdf')) iconClass = 'fa-file-pdf pdf';
            else if (ext.includes('xls')) iconClass = 'fa-file-excel xlsx';

            const fileSize = formatFileSize(doc.file_size_bytes);
            const date = formatDate(doc.uploaded_at);

            // Build tags HTML
            const tagsHtml = doc.tags && doc.tags.length
                ? `<div class="doc-tags">${doc.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>`
                : '';

            card.innerHTML = `
                <div class="doc-header">
                    <i class="fas ${iconClass} doc-icon"></i>
                    <div class="doc-info">
                        <h4>${doc.filename}</h4>
                        <div class="doc-meta">
                            <span>${date}</span>
                            <span>•</span>
                            <span>${fileSize}</span>
                        </div>
                    </div>
                </div>
                ${tagsHtml}
            `;

            docListContainer.appendChild(card);
        });
    }

    // --- Modal Logic ---

    closeModal.onclick = () => modal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target == modal) modal.style.display = 'none';
    };

    async function openModal(docId) {
        currentDocId = docId;
        modal.style.display = 'block';

        // Reset fields
        modalFilename.textContent = 'Cargando...';
        summaryResult.style.display = 'none';
        summaryResult.textContent = '';

        try {
            const response = await fetch(`/api/v1/documents/${docId}`);
            if (!response.ok) throw new Error('Error cargando detalles');

            const doc = await response.json();

            modalFilename.textContent = doc.filename;
            modalType.textContent = (doc.file_type || 'UNK').toUpperCase().replace('.', '');
            modalId.textContent = doc.document_id.substring(0, 8) + '...';
            modalDate.textContent = formatDate(doc.uploaded_at);
            modalSize.textContent = formatFileSize(doc.file_size_bytes);
            modalChunks.textContent = doc.chunk_count;

            // Inputs
            modalTags.value = doc.tags ? doc.tags.join(', ') : '';
            modalDesc.value = doc.description || '';

        } catch (error) {
            console.error(error);
            alert('No se pudo cargar el documento');
            modal.style.display = 'none';
        }
    }

    saveMetaBtn.onclick = async () => {
        if (!currentDocId) return;

        const tags = modalTags.value.split(',').map(t => t.trim()).filter(t => t);
        const description = modalDesc.value;

        try {
            const response = await fetch(`/api/v1/documents/${currentDocId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tags, description })
            });

            if (response.ok) {
                alert('Información actualizada');
                // Refresh local data to reflect changes immediately in list? 
                loadDocuments(); // Refresh list under modal
            } else {
                alert('Error al actualizar');
            }
        } catch (e) {
            alert('Error de conexión');
        }
    };

    deleteDocBtn.onclick = async () => {
        if (!currentDocId || !confirm('¿Estás seguro de eliminar este documento? Esta acción no se puede deshacer.')) return;

        try {
            const response = await fetch(`/api/v1/documents/${currentDocId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                modal.style.display = 'none';
                loadDocuments();
                fetchStats();
            } else {
                alert('Error al eliminar');
            }
        } catch (e) {
            alert('Error de conexión');
        }
    };

    genSummaryBtn.onclick = async () => {
        if (!currentDocId) return;

        summaryResult.style.display = 'block';
        summaryResult.textContent = 'Generando resumen...';

        try {
            const response = await fetch(`/api/v1/documents/${currentDocId}/summary`);
            const data = await response.json();

            if (response.ok) {
                summaryResult.textContent = data.summary;
            } else {
                summaryResult.textContent = 'Error: ' + data.detail;
            }
        } catch (e) {
            summaryResult.textContent = 'Error de conexión';
        }
    };

    // --- Helpers ---

    async function fetchStats() {
        try {
            const response = await fetch('/api/v1/documents/stats/advanced');
            if (response.ok) {
                const data = await response.json();
                docCount.textContent = data.total_documents;
                // modelName.textContent = ... (not in advanced stats, keep logic if exists elsewhere)
            }

            // Also fetch basic stats for model name
            const basicRes = await fetch('/api/v1/stats');
            if (basicRes.ok) {
                const basicData = await basicRes.json();
                modelName.textContent = basicData.model || 'Unknown';
            }

        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }

    function formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatDate(isoString) {
        if (!isoString) return '-';
        return new Date(isoString).toLocaleDateString();
    }
});
