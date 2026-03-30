const chatContainer = document.getElementById("chat-container");
const inputForm = document.getElementById("input-form");
const inputField = document.getElementById("input-field");
const sendBtn = document.getElementById("send-btn");

let threadId = null;

function addMessage(content, role) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  if (role === "agent") {
    div.innerHTML = renderMarkdown(content);
  } else {
    div.textContent = content;
  }
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showThinking() {
  const div = document.createElement("div");
  div.className = "thinking";
  div.id = "thinking-indicator";
  div.innerHTML = `Thinking <span class="dots"><span>.</span><span>.</span><span>.</span></span>`;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function hideThinking() {
  const el = document.getElementById("thinking-indicator");
  if (el) el.remove();
}

function showApproval(description, tId) {
  const div = document.createElement("div");
  div.className = "approval-banner";
  div.id = "approval-banner";
  div.innerHTML = `
    <h3>Mutation Approval Required</h3>
    <div>${renderMarkdown(description)}</div>
    <div class="approval-actions">
      <button class="btn-approve" onclick="handleApproval(true, '${tId}')">Approve</button>
      <button class="btn-reject" onclick="handleApproval(false, '${tId}')">Reject</button>
    </div>
  `;
  chatContainer.appendChild(div);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeApproval() {
  const el = document.getElementById("approval-banner");
  if (el) el.remove();
}

async function handleApproval(approved, tId) {
  removeApproval();
  addMessage(approved ? "Approved" : "Rejected", "user");
  showThinking();
  setInputEnabled(false);

  try {
    const res = await fetch("/api/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ thread_id: tId, approved }),
    });
    const data = await res.json();
    hideThinking();

    if (data.type === "approval_required") {
      showApproval(data.description, data.thread_id);
    } else {
      addMessage(data.content, "agent");
    }
  } catch (err) {
    hideThinking();
    addMessage(`Error: ${err.message}`, "agent");
  }
  setInputEnabled(true);
}

function setInputEnabled(enabled) {
  inputField.disabled = !enabled;
  sendBtn.disabled = !enabled;
  if (enabled) inputField.focus();
}

inputForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = inputField.value.trim();
  if (!message) return;

  addMessage(message, "user");
  inputField.value = "";
  showThinking();
  setInputEnabled(false);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, thread_id: threadId }),
    });
    const data = await res.json();
    hideThinking();

    threadId = data.thread_id;

    if (data.type === "approval_required") {
      showApproval(data.description, data.thread_id);
    } else {
      addMessage(data.content, "agent");
    }
  } catch (err) {
    hideThinking();
    addMessage(`Error: ${err.message}`, "agent");
  }
  setInputEnabled(true);
});

// Basic markdown renderer
function renderMarkdown(text) {
  if (!text) return "";
  let html = text
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>")
    // Inline code
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    // Bold
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Headers
    .replace(/^### (.+)$/gm, "<h4>$1</h4>")
    .replace(/^## (.+)$/gm, "<h3>$1</h3>")
    .replace(/^# (.+)$/gm, "<h2>$1</h2>")
    // Unordered lists
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    // Tables (simple)
    .replace(/\|(.+)\|/g, (match) => {
      const cells = match
        .split("|")
        .filter((c) => c.trim())
        .map((c) => c.trim());
      if (cells.every((c) => /^[-:]+$/.test(c))) return "";
      const tag = "td";
      return (
        "<tr>" + cells.map((c) => `<${tag}>${c}</${tag}>`).join("") + "</tr>"
      );
    });

  // Wrap list items
  html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");
  // Wrap table rows
  html = html.replace(/((?:<tr>.*<\/tr>\n?)+)/g, "<table>$1</table>");
  // Paragraphs
  html = html
    .split("\n\n")
    .map((p) => {
      p = p.trim();
      if (
        !p ||
        p.startsWith("<h") ||
        p.startsWith("<ul") ||
        p.startsWith("<pre") ||
        p.startsWith("<table")
      )
        return p;
      return `<p>${p}</p>`;
    })
    .join("\n");

  return html;
}
