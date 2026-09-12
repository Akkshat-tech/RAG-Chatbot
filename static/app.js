const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const modePill = document.getElementById("modePill");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const latencyFoot = document.getElementById("latencyFoot");
const reindexBtn = document.getElementById("reindexBtn");
const reindexStatus = document.getElementById("reindexStatus");

let sessionId = localStorage.getItem("cm_session_id") || null;

function setActiveModeButton(mode) {
  document.querySelectorAll(".mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === `:${mode}`);
  });
}

function addMessage(role, text, meta) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);

  if (role === "assistant" && meta) {
    const row = document.createElement("div");
    row.className = "meta-row";

    if (meta.sources && meta.sources.length) {
      const tag = document.createElement("span");
      tag.className = "meta-tag";
      tag.textContent = `sources: ${meta.sources.join(", ")}`;
      row.appendChild(tag);
    }
    if (meta.grounded !== null && meta.grounded !== undefined) {
      const tag = document.createElement("span");
      tag.className = `meta-tag ${meta.grounded ? "grounded" : "ungrounded"}`;
      tag.textContent = meta.grounded ? "grounded ✓" : "check grounding ⚠";
      row.appendChild(tag);
    }
    if (meta.breadth) {
      const tag = document.createElement("span");
      tag.className = "meta-tag";
      tag.textContent = `retrieval: ${meta.breadth}`;
      row.appendChild(tag);
    }
    if (meta.cached) {
      const tag = document.createElement("span");
      tag.className = "meta-tag";
      tag.textContent = "cached";
      row.appendChild(tag);
    }
    if (row.childNodes.length) wrap.appendChild(row);
  }

  chatWindow.appendChild(wrap);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage(text) {
  addMessage("user", text);
  chatInput.value = "";
  chatInput.disabled = true;

  // Create streaming assistant message bubble with blinking cursor
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const textSpan = document.createElement("span");
  const cursor = document.createElement("span");
  cursor.className = "cursor";

  bubble.appendChild(textSpan);
  bubble.appendChild(cursor);
  wrap.appendChild(bubble);
  chatWindow.appendChild(wrap);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  let accumulatedText = "";
  let finalMeta = null;

  try {
    const resp = await fetch("/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });

    if (!resp.ok) {
      let detail = `Server error (HTTP ${resp.status})`;
      try {
        const errData = await resp.json();
        detail = errData.detail || errData.answer || detail;
      } catch (_) {
        const rawText = await resp.text();
        if (rawText) detail = rawText;
      }
      throw new Error(detail);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const item = JSON.parse(line);
          if (item.type === "token") {
            accumulatedText += item.token;
            textSpan.textContent = accumulatedText;
            chatWindow.scrollTop = chatWindow.scrollHeight;
          } else if (item.type === "meta") {
            finalMeta = item.data;
          } else if (item.type === "error") {
            accumulatedText += `\n\n[Error: ${item.error}]`;
            textSpan.textContent = accumulatedText;
          }
        } catch (e) {
          console.error("Failed to parse JSON stream chunk:", line, e);
        }
      }
    }

    // Remove cursor when finished
    cursor.remove();

    if (finalMeta) {
      sessionId = finalMeta.session_id;
      if (sessionId) localStorage.setItem("cm_session_id", sessionId);

      const row = document.createElement("div");
      row.className = "meta-row";

      if (finalMeta.sources && finalMeta.sources.length) {
        const tag = document.createElement("span");
        tag.className = "meta-tag";
        tag.textContent = `sources: ${finalMeta.sources.join(", ")}`;
        row.appendChild(tag);
      }
      if (finalMeta.grounded !== null && finalMeta.grounded !== undefined) {
        const tag = document.createElement("span");
        tag.className = `meta-tag ${finalMeta.grounded ? "grounded" : "ungrounded"}`;
        tag.textContent = finalMeta.grounded ? "grounded ✓" : "check grounding ⚠";
        row.appendChild(tag);
      }
      if (finalMeta.breadth) {
        const tag = document.createElement("span");
        tag.className = "meta-tag";
        tag.textContent = `retrieval: ${finalMeta.breadth}`;
        row.appendChild(tag);
      }
      if (finalMeta.cached) {
        const tag = document.createElement("span");
        tag.className = "meta-tag";
        tag.textContent = "cached";
        row.appendChild(tag);
      }
      if (row.childNodes.length) wrap.appendChild(row);

      if (finalMeta.mode) {
        modePill.textContent = finalMeta.mode.toUpperCase();
        setActiveModeButton(finalMeta.mode);
      }
      if (finalMeta.latency_ms !== undefined) {
        latencyFoot.textContent = `last response: ${finalMeta.latency_ms} ms${finalMeta.cached ? " (cache hit)" : ""}`;
      }
    }
  } catch (err) {
    cursor.remove();
    textSpan.textContent = (accumulatedText ? accumulatedText + "\n\n" : "") + `Error talking to the backend: ${err}. Is the FastAPI server (and Ollama) running?`;
  } finally {
    chatInput.disabled = false;
    chatInput.focus();
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (text) sendMessage(text);
});

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    sendMessage(btn.dataset.mode);
  });
});

reindexBtn.addEventListener("click", async () => {
  reindexBtn.disabled = true;
  reindexStatus.textContent = "Rebuilding index…";
  try {
    const resp = await fetch("/reindex", { method: "POST" });
    const data = await resp.json();
    reindexStatus.textContent = `Indexed ${data.chunks} chunks from ${data.documents} documents.`;
  } catch (err) {
    reindexStatus.textContent = `Failed: ${err}`;
  } finally {
    reindexBtn.disabled = false;
  }
});

const clearSessionBtn = document.getElementById("clearSessionBtn");
clearSessionBtn.addEventListener("click", () => {
  console.log("Clearing session and reloading...");
  localStorage.removeItem("cm_session_id");
  sessionId = null;
  // Force hard reload to clear all state
  window.location.reload(true);
});

async function checkHealth() {
  try {
    const resp = await fetch("/health");
    const data = await resp.json();
    if (data.ollama.reachable) {
      statusDot.className = "status-pill status-ok";
      statusText.textContent = `online · ${data.knowledge_base_chunks} chunks indexed`;
    } else {
      statusDot.className = "status-pill status-error";
      statusText.textContent = "Ollama unreachable";
    }
  } catch (err) {
    statusDot.className = "status-pill status-error";
    statusText.textContent = "backend unreachable";
  }
}

checkHealth();
setInterval(checkHealth, 15000);
