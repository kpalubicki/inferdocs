let documents = [];
let selectedDocId = null;
let currentMode = 'ask';
let currentStyle = 'brief';
let streaming = false;

const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const docsList = document.getElementById('docsList');
const docDot = document.getElementById('docDot');
const docIndicatorText = document.getElementById('docIndicatorText');
const askPanel = document.getElementById('askPanel');
const summarizePanel = document.getElementById('summarizePanel');
const historyPanel = document.getElementById('historyPanel');
const outputCard = document.getElementById('outputCard');
const questionInput = document.getElementById('questionInput');
const sendBtn = document.getElementById('sendBtn');
const summarizeBtn = document.getElementById('summarizeBtn');
const maxLength = document.getElementById('maxLength');
const output = document.getElementById('output');
const outputLabel = document.getElementById('outputLabel');
const spinner = document.getElementById('spinner');
const copyBtn = document.getElementById('copyBtn');
const historyList = document.getElementById('historyList');
const historyCount = document.getElementById('historyCount');
const exportMdBtn = document.getElementById('exportMdBtn');
const exportJsonBtn = document.getElementById('exportJsonBtn');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');

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
    historyPanel.style.display = currentMode === 'history' ? 'block' : 'none';
    outputCard.style.display = currentMode === 'history' ? 'none' : 'block';
    if (currentMode === 'history') loadHistory();
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
copyBtn.addEventListener('click', () => {
  navigator.clipboard.writeText(output.textContent).then(() => {
    copyBtn.textContent = 'Copied!';
    setTimeout(() => { copyBtn.textContent = 'Copy'; }, 1500);
  });
});

exportMdBtn.addEventListener('click', () => downloadHistory('md'));
exportJsonBtn.addEventListener('click', () => downloadHistory('json'));
clearHistoryBtn.addEventListener('click', clearHistory);

// Init
loadDocuments();

// --- Upload ---
async function handleUpload(file) {
  const form = new FormData();
  form.append('file', file);
  showStatus('Uploading\u2026', null);

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
      <span class="doc-icon">${doc.file_type === '.pdf' ? '\uD83D\uDCCB' : '\uD83D\uDCDD'}</span>
      <span class="doc-name">${escapeHtml(doc.filename)}</span>
      <span class="doc-delete" data-id="${doc.document_id}" title="Delete">&times;</span>
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
  if (currentMode === 'history') loadHistory();
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

// --- Ask (streaming) ---
async function send() {
  const question = questionInput.value.trim();
  if (!question || streaming) return;
  if (!selectedDocId) { setOutput('Select a document first.', true); return; }

  setLoading(true, 'Thinking\u2026');
  output.textContent = '';
  let fullText = '';

  try {
    const res = await fetch(`/documents/${selectedDocId}/ask/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });

    if (!res.ok) {
      const data = await res.json();
      setOutput(data.error ?? data.detail ?? 'Something went wrong.', true);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n\n');
      buf = lines.pop() ?? '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const ev = JSON.parse(line.slice(6));
          if (ev.token) {
            fullText += ev.token;
            output.textContent = fullText;
            output.style.color = 'var(--text-muted)';
          }
          if (ev.done) {
            outputLabel.textContent = 'Answer';
            copyBtn.style.display = '';
          }
        } catch {}
      }
    }
  } catch (e) {
    setOutput(e.message, true);
  } finally {
    setLoading(false);
  }
}

// --- Summarize (streaming) ---
async function runSummarize() {
  if (!selectedDocId || streaming) return;
  if (!selectedDocId) { setOutput('Select a document first.', true); return; }

  setLoading(true, 'Summarizing\u2026');
  output.textContent = '';
  let fullText = '';

  try {
    const res = await fetch(`/documents/${selectedDocId}/summarize/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style: currentStyle, max_length: parseInt(maxLength.value) || 150 }),
    });

    if (!res.ok) {
      const data = await res.json();
      setOutput(data.error ?? data.detail ?? 'Something went wrong.', true);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n\n');
      buf = lines.pop() ?? '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);
        if (payload === '[DONE]') {
          outputLabel.textContent = 'Summary';
          copyBtn.style.display = '';
          break;
        }
        if (payload === '[ERROR]') {
          setOutput('Streaming error.', true);
          break;
        }
        fullText += payload;
        output.textContent = fullText;
        output.style.color = 'var(--text-muted)';
      }
    }
  } catch (e) {
    setOutput(e.message, true);
  } finally {
    setLoading(false);
  }
}

// --- History ---
async function loadHistory() {
  if (!selectedDocId) {
    historyList.innerHTML = '<p class="history-empty">Select a document to view its conversation history.</p>';
    historyCount.textContent = '';
    return;
  }

  try {
    const res = await fetch(`/documents/${selectedDocId}/history`);
    const data = await res.json();
    renderHistory(data.entries ?? [], data.count ?? 0, data.filename ?? '');
  } catch (e) {
    historyList.innerHTML = '<p class="history-empty">Failed to load history.</p>';
  }
}

function renderHistory(entries, count, filename) {
  historyCount.textContent = `${count} exchange${count !== 1 ? 's' : ''} for ${escapeHtml(filename)}`;

  if (entries.length === 0) {
    historyList.innerHTML = '<p class="history-empty">No conversations recorded yet. Ask a question to start.</p>';
    return;
  }

  historyList.innerHTML = entries.map((e, i) => `
    <div class="history-card">
      <div class="history-card-header">
        <span class="history-q-label">Q${i + 1}</span>
        <span class="history-timestamp">${formatTimestamp(e.timestamp)}</span>
      </div>
      <div class="history-question">${escapeHtml(e.question)}</div>
      <div class="history-answer">${escapeHtml(e.answer)}</div>
    </div>
  `).join('');
}

async function downloadHistory(format) {
  if (!selectedDocId) return;
  const url = `/documents/${selectedDocId}/history/export?format=${format}`;
  const a = document.createElement('a');
  a.href = url;
  a.download = '';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

async function clearHistory() {
  if (!selectedDocId) return;
  if (!confirm('Clear all conversation history for this document?')) return;
  try {
    await fetch(`/documents/${selectedDocId}/history`, { method: 'DELETE' });
    await loadHistory();
  } catch (e) {
    console.error('Clear failed', e);
  }
}

// --- Helpers ---
function setLoading(on, label = '') {
  streaming = on;
  spinner.classList.toggle('active', on);
  outputLabel.textContent = on ? label : 'Output';
  sendBtn.disabled = on;
  summarizeBtn.disabled = on;
  if (on) {
    copyBtn.style.display = 'none';
    output.style.color = 'var(--text-muted)';
  }
}

function setOutput(text, isError = false) {
  output.style.color = isError ? 'var(--error)' : 'var(--text-muted)';
  output.textContent = text;
  copyBtn.style.display = isError ? 'none' : '';
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

function formatTimestamp(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return iso;
  }
}
