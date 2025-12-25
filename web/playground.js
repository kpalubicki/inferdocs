// InferDocs Playground JavaScript

let documents = [];

// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');
const refreshBtn = document.getElementById('refreshBtn');
const documentsList = document.getElementById('documentsList');
const documentSelect = document.getElementById('documentSelect');
const modeRadios = document.querySelectorAll('input[name="mode"]');
const questionGroup = document.getElementById('questionGroup');
const questionInput = document.getElementById('questionInput');
const streamCheckbox = document.getElementById('streamCheckbox');
const sendBtn = document.getElementById('sendBtn');
const output = document.getElementById('output');

// Event Listeners
uploadBtn.addEventListener('click', uploadDocument);
refreshBtn.addEventListener('click', loadDocuments);
modeRadios.forEach(radio => radio.addEventListener('change', toggleQuestionInput));
sendBtn.addEventListener('click', handleSend);

// Initialize
loadDocuments();

// Upload Document
async function uploadDocument() {
    const file = fileInput.files[0];
    if (!file) {
        showStatus('Please select a file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        uploadBtn.disabled = true;
        showStatus('Uploading...', 'info');

        const response = await fetch('/documents', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(`Success: ${data.message}`, 'success');
            fileInput.value = '';
            loadDocuments();
        } else {
            showStatus(`Error: ${data.error || data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        uploadBtn.disabled = false;
    }
}

// Load Documents List
async function loadDocuments() {
    try {
        const response = await fetch('/documents');
        const data = await response.json();

        documents = data.documents || [];
        displayDocuments();
        updateDocumentSelect();
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

// Display Documents in List
function displayDocuments() {
    if (documents.length === 0) {
        documentsList.innerHTML = '<p class="placeholder">No documents uploaded yet.</p>';
        return;
    }

    documentsList.innerHTML = documents.map(doc => `
        <div class="document-item">
            <div class="document-name">${escapeHtml(doc.filename)}</div>
            <div class="document-meta">
                ID: ${doc.document_id.substring(0, 8)}... |
                Type: ${doc.file_type} |
                Size: ${formatBytes(doc.file_size)}
            </div>
        </div>
    `).join('');
}

// Update Document Select Dropdown
function updateDocumentSelect() {
    documentSelect.innerHTML = '<option value="">-- Select a document --</option>';

    documents.forEach(doc => {
        const option = document.createElement('option');
        option.value = doc.document_id;
        option.textContent = doc.filename;
        documentSelect.appendChild(option);
    });
}

// Toggle Question Input
function toggleQuestionInput() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    questionGroup.style.display = mode === 'ask' ? 'block' : 'none';
}

// Handle Send Button
async function handleSend() {
    const documentId = documentSelect.value;
    if (!documentId) {
        alert('Please select a document');
        return;
    }

    const mode = document.querySelector('input[name="mode"]:checked').value;
    const useStream = streamCheckbox.checked;

    if (mode === 'summarize') {
        await summarizeDocument(documentId, useStream);
    } else {
        const question = questionInput.value.trim();
        if (!question) {
            alert('Please enter a question');
            return;
        }
        await askQuestion(documentId, question, useStream);
    }
}

// Summarize Document
async function summarizeDocument(documentId, useStream) {
    try {
        sendBtn.disabled = true;
        output.innerHTML = '<div class="spinner"></div>';
        output.classList.add('loading');

        const response = await fetch(`/documents/${documentId}/summarize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });

        const data = await response.json();

        if (response.ok) {
            output.classList.remove('loading');
            output.textContent = data.summary;
        } else {
            output.classList.remove('loading');
            output.innerHTML = `<span style="color: red;">Error: ${data.error || data.detail}</span>`;
        }
    } catch (error) {
        output.classList.remove('loading');
        output.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
    } finally {
        sendBtn.disabled = false;
    }
}

// Ask Question
async function askQuestion(documentId, question, useStream) {
    try {
        sendBtn.disabled = true;
        output.innerHTML = '<div class="spinner"></div>';
        output.classList.add('loading');

        const response = await fetch(`/documents/${documentId}/ask`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        if (response.ok) {
            output.classList.remove('loading');
            output.innerHTML = `
                <strong>Question:</strong> ${escapeHtml(question)}<br><br>
                <strong>Answer:</strong> ${escapeHtml(data.answer)}
            `;
        } else {
            output.classList.remove('loading');
            output.innerHTML = `<span style="color: red;">Error: ${data.error || data.detail}</span>`;
        }
    } catch (error) {
        output.classList.remove('loading');
        output.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
    } finally {
        sendBtn.disabled = false;
    }
}

// Show Upload Status
function showStatus(message, type) {
    uploadStatus.textContent = message;
    uploadStatus.className = `status-message ${type}`;

    if (type === 'success') {
        setTimeout(() => {
            uploadStatus.textContent = '';
            uploadStatus.className = 'status-message';
        }, 3000);
    }
}

// Utility Functions
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
