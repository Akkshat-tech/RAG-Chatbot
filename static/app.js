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

  const thinking = document.createElement("div");
  thinking.className = "msg assistant";
  thinking.innerHTML = '<div class="bubble">…</div>';
  chatWindow.appendChild(thinking);
  chatWindow.scrollTop = chatWindow.scrollHeight;

  try {
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await resp.json();
    sessionId = data.session_id;
    localStorage.setItem("cm_session_id", sessionId);

    thinking.remove();
    addMessage("assistant", data.answer, {
      sources: data.sources,
      grounded: data.grounded,
      breadth: data.breadth,
      cached: data.cached,
    });

    modePill.textContent = data.mode.toUpperCase();
    setActiveModeButton(data.mode);
    latencyFoot.textContent = `last response: ${data.latency_ms} ms${data.cached ? " (cache hit)" : ""}`;
  } catch (err) {
    thinking.remove();
    addMessage("assistant", `Error talking to the backend: ${err}. Is the FastAPI server (and Ollama) running?`);
  } finally {
    chatInput.disabled = false;
    chatInput.focus();
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
