const messageList = document.getElementById("message-list");
const chatForm = document.getElementById("chat-form");
const queryInput = document.getElementById("query-input");
const apiBaseInput = document.getElementById("api-base");
const apiPreview = document.getElementById("api-preview");
const statusText = document.getElementById("status-text");
const sendButton = document.getElementById("send-btn");
const clearButton = document.getElementById("clear-btn");
const charCount = document.getElementById("char-count");
const promptChips = document.querySelectorAll(".prompt-chip");

const SESSION_STORAGE_KEY = "chat-session-id";
const USER_STORAGE_KEY = "chat-user-id";

function createSessionId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createUserId() {
  if (window.crypto?.randomUUID) {
    return `user-${window.crypto.randomUUID()}`;
  }

  return `user-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getOrCreateSessionId() {
  const savedSessionId = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (savedSessionId) {
    return savedSessionId;
  }

  const newSessionId = createSessionId();
  window.localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);
  return newSessionId;
}

function getOrCreateUserId() {
  const savedUserId = window.localStorage.getItem(USER_STORAGE_KEY);
  if (savedUserId) {
    return savedUserId;
  }

  const newUserId = createUserId();
  window.localStorage.setItem(USER_STORAGE_KEY, newUserId);
  return newUserId;
}

function resetSessionId() {
  const newSessionId = createSessionId();
  window.localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);
  return newSessionId;
}

let sessionId = getOrCreateSessionId();
const userId = getOrCreateUserId();

function getTimestampLabel() {
  const now = new Date();
  return now.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function updateApiPreview() {
  const apiBase = apiBaseInput.value.trim() || "未设置";
  apiPreview.textContent = apiBase.replace(/\/$/, "");
}

function updateCharCount() {
  const count = queryInput.value.trim().length;
  charCount.textContent = `${count} 字`;
}

function createMessage(role, content = "") {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const badge = document.createElement("div");
  badge.className = "message-badge";
  badge.textContent = role === "user" ? "客户" : "AI 顾问";

  const paragraph = document.createElement("p");
  paragraph.textContent = content;

  const time = document.createElement("time");
  time.className = "message-time";
  time.textContent = getTimestampLabel();

  article.appendChild(badge);
  article.appendChild(paragraph);
  article.appendChild(time);

  messageList.appendChild(article);
  messageList.scrollTop = messageList.scrollHeight;
  return { article, paragraph, time };
}

function renderMessage(role, content) {
  return createMessage(role, content);
}

function setSubmitting(isSubmitting) {
  sendButton.disabled = isSubmitting;
  clearButton.disabled = isSubmitting;
  queryInput.disabled = isSubmitting;
  apiBaseInput.disabled = isSubmitting;

  for (const chip of promptChips) {
    chip.disabled = isSubmitting;
  }

  statusText.textContent = isSubmitting ? "正在连接智能客服引擎..." : "等待输入";
}

function readSseChunk(buffer) {
  const separator = "\n\n";
  const index = buffer.indexOf(separator);
  if (index === -1) {
    return null;
  }

  const rawEvent = buffer.slice(0, index);
  const rest = buffer.slice(index + separator.length);
  return { rawEvent, rest };
}

async function submitQuery(query) {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    statusText.textContent = "请输入咨询内容";
    return;
  }

  const apiBase = apiBaseInput.value.trim().replace(/\/$/, "");
  const payload = { query: normalizedQuery, session_id: sessionId, user_id: userId };

  renderMessage("user", normalizedQuery);
  queryInput.value = "";
  updateCharCount();
  setSubmitting(true);

  const assistantMessage = createMessage("assistant", "正在分析你的问题，并准备生成专业答复...");
  let finalAnswer = "";
  let streamedAnswer = "";
  let hasStartedStreaming = false;

  try {
    const response = await fetch(`${apiBase}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      while (true) {
        const parsed = readSseChunk(buffer);
        if (!parsed) {
          break;
        }

        buffer = parsed.rest;
        const dataLine = parsed.rawEvent
          .split("\n")
          .find((line) => line.startsWith("data: "));

        if (!dataLine) {
          continue;
        }

        const payloadText = dataLine.slice(6);
        const eventData = JSON.parse(payloadText);

        if (eventData.type === "snapshot") {
          assistantMessage.paragraph.textContent = eventData.content;
          statusText.textContent = "正在整理分析路径...";
        }

        if (eventData.type === "delta") {
          if (!hasStartedStreaming) {
            streamedAnswer = "";
            assistantMessage.paragraph.textContent = "";
            hasStartedStreaming = true;
          }

          streamedAnswer += eventData.content || "";
          assistantMessage.paragraph.textContent = streamedAnswer;
          statusText.textContent = "正在生成最终回复...";
        }

        if (eventData.type === "final") {
          finalAnswer = eventData.content?.trim() || "后端返回了空结果。";
          assistantMessage.paragraph.textContent = finalAnswer;
          statusText.textContent = "响应完成";
        }

        messageList.scrollTop = messageList.scrollHeight;
      }
    }

    if (!finalAnswer) {
      finalAnswer = assistantMessage.paragraph.textContent.trim() || "后端返回了空结果。";
      assistantMessage.paragraph.textContent = finalAnswer;
      statusText.textContent = "响应完成";
    }
  } catch (error) {
    assistantMessage.paragraph.textContent = `请求失败：${error.message}`;
    statusText.textContent = "请求失败";
  } finally {
    setSubmitting(false);
    queryInput.focus();
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await submitQuery(queryInput.value);
});

clearButton.addEventListener("click", () => {
  sessionId = resetSessionId();
  messageList.innerHTML = "";
  renderMessage("assistant", "新会话已建立。你可以继续咨询产品、故障、保养建议或月度报告。");
  statusText.textContent = "已切换到新会话";
  queryInput.value = "";
  updateCharCount();
  queryInput.focus();
});

queryInput.addEventListener("input", updateCharCount);
apiBaseInput.addEventListener("input", updateApiPreview);

for (const chip of promptChips) {
  chip.addEventListener("click", () => {
    queryInput.value = chip.dataset.prompt || "";
    updateCharCount();
    queryInput.focus();
  });
}

updateApiPreview();
updateCharCount();
