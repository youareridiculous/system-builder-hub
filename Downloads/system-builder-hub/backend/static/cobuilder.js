(function(){
  const ta = document.getElementById('cb-input');
  const send = document.getElementById('cb-send');
  const cancelBtn = document.getElementById('cb-cancel');
  const transcript = document.getElementById('cb-transcript');
  const messages = transcript; // Alias for compatibility
  
  // Get tenant ID from data attribute or default to demo
  const tenantId = document.getElementById('cb-root')?.dataset?.tenant || 'demo';
  
  let inflight = null;

  // Auto-resize textarea
  function autoSize() {
    ta.style.height = 'auto';
    const maxH = Math.floor(window.innerHeight * 0.40);
    ta.style.height = Math.min(ta.scrollHeight, maxH) + 'px';
  }

  // Update character and token counters
  function updateCounters() {
    const len = ta.value.length;
    const maxChars = parseInt(ta.getAttribute('maxlength') || '10000', 10);
    const warnAt = Math.floor(maxChars * 0.9);
    const hardAt = maxChars;
    
    // Update character counter
    const counter = document.getElementById('cb-counter');
    if (counter) {
      counter.textContent = `${len.toLocaleString()} / ${maxChars.toLocaleString()}`;
      counter.classList.toggle('cb-warn', len >= warnAt && len < hardAt);
      counter.classList.toggle('cb-hard', len >= hardAt);
    }
    
    // Update token estimate
    const tokens = document.getElementById('cb-tokens');
    if (tokens) {
      const estTokens = Math.ceil(len / 4);
      tokens.textContent = `~${estTokens.toLocaleString()} tokens`;
      tokens.classList.toggle('cb-warn', len >= warnAt && len < hardAt);
      tokens.classList.toggle('cb-hard', len >= hardAt);
    }
  }

  // Draft persistence
  const DRAFT_KEY = 'cb_draft';
  function persistDraft() {
    localStorage.setItem(DRAFT_KEY, ta.value);
  }
  
  function clearDraft() {
    localStorage.removeItem(DRAFT_KEY);
    ta.value = '';
    autoSize();
    updateCounters();
  }

  // Restore draft on load
  const saved = localStorage.getItem(DRAFT_KEY);
  if (saved) {
    ta.value = saved;
    updateCounters();
  }

  // Add message to transcript
  function addMessage(content, isUser = false, id = null) {
    const div = document.createElement('div');
    div.className = `cb-msg ${isUser ? 'user' : 'assistant'}`;
    div.innerHTML = content;
    if (id) div.id = id;
    transcript.appendChild(div);
    transcript.scrollTop = transcript.scrollHeight;
  }

  // Hide error message
  function hideError() {
    const errorDiv = document.querySelector('.cb-error');
    if (errorDiv) errorDiv.remove();
  }

  // Main send function
  async function cobuilderSend(){
    const text = ta.value.trim();
    if (!text) return;
    
    // Guard against double-send
    if (inflight) {
      cancelBtn.focus();
      return;
    }

    // Disable send button and show sending state
    send.disabled = true;
    send.classList.add('sending');
    cancelBtn.disabled = false;
    hideError();

    // Add user message immediately
    addMessage(text, true);

    // Add "Thinking..." placeholder
    const thinkingId = 'thinking-' + Date.now();
    addMessage('🤔 Thinking... <span class="cb-timer">(0:00)</span>', false, thinkingId);
    
    // Start timer
    const timerStart = Date.now();
    const timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - timerStart) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      const timerEl = document.querySelector(`#${thinkingId} .cb-timer`);
      if (timerEl) {
        timerEl.textContent = `(${minutes}:${seconds.toString().padStart(2, '0')})`;
      }
    }, 1000);

    // Create abort controller and track in-flight request
    const controller = new AbortController();
    inflight = { controller, thinkingId, sentText: text };

    let response, data;
    
    try {
      // Make API request (no artificial timeout)
      response = await fetch('/api/cobuilder/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': tenantId,
          'Cache-Control': 'no-store'
        },
        body: JSON.stringify({
          message: text,
          tenant_id: tenantId,
          dry_run: false
        }),
        signal: controller.signal
      });

      // Parse response JSON (never throw on parse)
      try { data = await response.json(); } catch { data = null; }

      const json = data || {};
      const ok = json?.success === true;

      // Compact single-line log
      console.log('ask:', {
        ok,
        status: response.status,
        requestId: json?.request_id,
        canceled: false
      });

      if (!ok) {
        // Log full JSON to assist debugging
        console.warn('ask full response:', json);
        const detail = json?.errors?.[0]?.detail || 'Request failed — please try again.';
        addMessage(detail, false);
        return; // Keep draft
      }

      // ----- SUCCESS PATH -----
      const d = json.data || {};
      const responseText =
        d.response ?? d.message ?? json.response ?? json.message ?? 'Change prepared.';

      addMessage(responseText, false);

      // Render file/diff/snippet when present
      if (d.file) {
        addAssistantLabel(`File: ${d.file}`);
      }
      if (d.diff) {
        addAssistantLabel('Proposed Change (Diff)');
        addAssistantCodeBlock(d.diff);
      }
      if (d.snippet) {
        addAssistantLabel('Test Snippet');
        addAssistantCodeBlock(d.snippet);
      }

      // Optional: show model/elapsed in logs only
      if (d.model || typeof d.elapsed_ms === 'number') {
        console.log('ask meta:', { model: d.model, elapsed_ms: d.elapsed_ms });
      }

      // Clear draft on success
      clearDraft();

    } catch (error) {
      const canceled = error?.name === 'AbortError';
      
      // Log compact error info
      console.log('ask:', {
        ok: false,
        status: response?.status,
        requestId: (data || {})?.request_id || (data || {})?.data?.request_id,
        canceled
      });
      
      // Show appropriate error message
      if (canceled) {
        addMessage('Request canceled.', false);
      } else {
        addMessage('Request failed — please try again.', false);
      }
      // Keep draft unchanged
    } finally {
      // Clear timer
      clearInterval(timerInterval);
      // Always cleanup (idempotent)
      try {
        // Remove thinking placeholder if it still exists
        const thinkingDiv = document.getElementById(thinkingId);
        if (thinkingDiv) thinkingDiv.remove();
      } catch (cleanupError) {
        console.warn('Cleanup error:', cleanupError);
      }
      
      // Re-enable send button and disable cancel
      send.disabled = false;
      send.classList.remove('sending');
      cancelBtn.disabled = true;
      cancelBtn.classList.remove('canceling');
      
      // Clear in-flight tracking
      inflight = null;
    }
  }

  // --- helpers to render labels and code blocks in assistant stream ---
  function addAssistantLabel(text){
    const div = document.createElement('div');
    div.className = 'cb-label';
    div.textContent = text;
    transcript.appendChild(div);
    transcript.scrollTop = transcript.scrollHeight;
  }

  function addAssistantCodeBlock(code){
    const pre = document.createElement('pre');
    pre.className = 'cb-code';
    pre.textContent = code;
    transcript.appendChild(pre);
    transcript.scrollTop = transcript.scrollHeight;
  }

  // Event listeners
  ta.addEventListener('input', () => {
    autoSize();
    updateCounters();
    persistDraft();
  });

  ta.addEventListener('keydown', (e) => {
    // Shift+Enter = newline (default behavior)
    if (e.key === 'Enter' && e.shiftKey) {
      return; // Allow default newline behavior
    }
    
    // Enter or Cmd/Ctrl+Enter = send
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      cobuilderSend();
    }
    
    // Cmd/Ctrl+Enter also sends
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      cobuilderSend();
    }
  });

  send.addEventListener('click', cobuilderSend);

  // Cancel button event handler
  cancelBtn.addEventListener('click', () => {
    if (!inflight) return;
    
    // Show canceling state
    cancelBtn.classList.add('canceling');
    
    try {
      inflight.controller.abort();
    } catch (e) {
      console.warn('Error aborting request:', e);
    }
  });

  // Initial setup
  autoSize();
  updateCounters();

  // Handle window resize for mobile keyboards
  window.addEventListener('resize', autoSize);

  // Expose the send function globally for the UI template to use
  window.cobuilderSend = cobuilderSend;
})();
