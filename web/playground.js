let documents = [];
let selectedDocId = null;
let currentMode = 'ask';
let currentStyle = 'brief';

const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const docsList = document.getElementById('docsList');
const docDot = document.getElementById('docDot');
const docIndicatorText = document.getElementById('docIndicatorText');
const askPanel = document.getElementById('askPanel');
const summarizePanel = document.getElementById('summarizePanel');
const questionInput = document.getElementById('questionInput');
const sendBtn = document.getElementById('sendBtn');
const summarizeBtn = document.getElementById('summarizeBtn');
const maxLength = document.getElementById('maxLength');
const output = document.getElementById('output');
const outputLabel = document.getElementById('outputLabel');
const spinner = document.getElementById('spinner');

// Upload zone
uploadZone.addEventListener('click', () => fileInput.click());
uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragging'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragging'));
uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('dragging');
  const file = e.dataTransfer.files[0];
  if (file) handleUpload(file);
});
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleUpload(fileInput.files[0]);
});

// Mode tabs
document.querySelectorAll('.mode-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    currentMode = tab.dataset.mode;
    askPanel.style.display = currentMode === 'ask' ? 'block' : 'none';
    summarizePanel.style.display = currentMode === 'summarize' ? 'block' : 'none';
  });
});

// Style buttons
document.querySelectorAll('.style-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentStyle = btn.dataset.style;
  });
});

// Send question on Enter
questionInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});

sendBtn.addEventListener('click', send);
summarizeBtn.addEventListener('click', runSummarize);

// Init
loadDocuments();

// --- Upload ---
async function handleUpload(file) {
  const form = new FormData();
  form.append('file', file);
  showStatus('Uploading…', null);

  try {
    const res = await fetch('/documents', { method: 'POST', body: form });
    const data = await res.json();
    if (res.ok) {
      showStatus(`Uploaded: ${data.filename ?? file.name}`, 'success');
      fileInput.value = '';
      await loadDocuments();
      selectDoc(data.document_id);
    } else {
      showStatus(data.error ?? data.detail ?? 'Upload failed', 'error');
    }
  } catch (e) {
    showStatus(e.message, 'error');
  }
}

// --- Load documents ---
async function loadDocuments() {
  try {
    const res = await fetch('/documents');
    const data = await res.json();
    documents = data.documents ?? [];
    renderDocs();
  } catch (e) {
    console.error('Failed to load documents', e);
  }
}

function renderDocs() {
  if (documents.length === 0) {
    docsList.innerHTML = '<p class="empty-docs">No documents yet</p>';
    return;
  }

  docsList.innerHTML = documents.map(doc => `
    <div class="doc-item ${doc.document_id === selectedDocId ? 'active' : ''}" data-id="${doc.document_id}">
      <span class="doc-icon">${doc.file_type === '.pdf' ? '📋' : '📝'}</span>
      <span class="doc-name">${escapeHtml(doc.filename)}</span>
      <span class="doc-delete" data-id="${doc.document_id}" title="Delete">✕</span>
    </div>
  `).join('');

  docsList.querySelectorAll('.doc-item').forEach(el => {
    el.addEventListener('click', () => selectDoc(el.dataset.id));
  });

  docsList.querySelectorAll('.doc-delete').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteDoc(el.dataset.id);
    });
  });
}

function selectDoc(id) {
  selectedDocId = id;
  const doc = documents.find(d => d.document_id === id);
  docDot.classList.toggle('active', !!doc);
  docIndicatorText.textContent = doc ? doc.filename : 'No document selected';
  renderDocs();
}

async function deleteDoc(id) {
  try {
    await fetch(`/documents/${id}`, { method: 'DELETE' });
    if (selectedDocId === id) {
      selectedDocId = null;
      docDot.classList.remove('active');
      docIndicatorText.textContent = 'No document selected';
    }
    await loadDocuments();
  } catch (e) {
    console.error('Delete failed', e);
  }
}

// --- Ask ---
async function send() {
  const question = questionInput.value.trim();
  if (!question) return;
  if (!selectedDocId) { setOutput('Select a document first.', true); return; }

  setLoading(true, 'Thinking…');

  try {
    const res = await fetch(`/documents/${selectedDocId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    if (res.ok) {
      setOutput(data.answer);
    } else {
      setOutput(data.error ?? data.detail ?? 'Something went wrong.', true);
    }
  } catch (e) {
    setOutput(e.message, true);
  } finally {
    setLoading(false);
  }
}

// --- Summarize ---
async function runSummarize() {
  if (!selectedDocId) { setOutput('Select a document first.', true); return; }

  setLoading(true, 'Summarizing…');

  try {
    const res = await fetch(`/documents/${selectedDocId}/summarize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: currentStyle, max_length: parseInt(maxLength.value) || 150 }),
    });
    const data = await res.json();
    if (res.ok) {
      setOutput(data.summary);
    } else {
      setOutput(data.error ?? data.detail ?? 'Something went wrong.', true);
    }
  } catch (e) {
    setOutput(e.message, true);
  } finally {
    setLoading(false);
  }
}

// --- Helpers ---
function setLoading(on, label = '') {
  spinner.classList.toggle('active', on);
  outputLabel.textContent = on ? label : 'Output';
  sendBtn.disabled = on;
  summarizeBtn.disabled = on;
  if (on) output.innerHTML = '';
}

function setOutput(text, isError = false) {
  output.style.color = isError ? 'var(--error)' : 'var(--text-muted)';
  output.textContent = text;
}

function showStatus(msg, type) {
  uploadStatus.textContent = msg;
  uploadStatus.className = `status-bar${type ? ' ' + type : ''}`;
  if (type === 'success') setTimeout(() => { uploadStatus.className = 'status-bar'; uploadStatus.textContent = ''; }, 3000);
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}
