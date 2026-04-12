const messageList = document.getElementById("message-list");
const chatForm = document.getElementById("chat-form");
const queryInput = document.getElementById("query-input");
const apiBaseInput = document.getElementById("api-base");
const statusText = document.getElementById("status-text");
const sendButton = document.getElementById("send-btn");
const clearButton = document.getElementById("clear-btn");

const SESSION_STORAGE_KEY = "chat-session-id";

function createSessionId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
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

function resetSessionId() {
  const newSessionId = createSessionId();
  window.localStorage.setItem(SESSION_STORAGE_KEY, newSessionId);
  return newSessionId;
}

// 前端不再维护完整 history，只保存用于绑定后端短期记忆的 session_id。
let sessionId = getOrCreateSessionId();

function createMessage(role, content = "") {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  article.appendChild(paragraph);

  messageList.appendChild(article);
  messageList.scrollTop = messageList.scrollHeight;
  return { article, paragraph };
}

function renderMessage(role, content) {
  return createMessage(role, content);
}

function setSubmitting(isSubmitting) {
  sendButton.disabled = isSubmitting;
  clearButton.disabled = isSubmitting;
  queryInput.disabled = isSubmitting;
  statusText.textContent = isSubmitting ? "正在流式接收后端响应..." : "等待输入";
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

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const query = queryInput.value.trim();
  if (!query) {
    statusText.textContent = "请输入问题";
    return;
  }

  const apiBase = apiBaseInput.value.trim().replace(/\/$/, "");
  const payload = { query, session_id: sessionId };

  renderMessage("user", query);
  queryInput.value = "";
  setSubmitting(true);

  const assistantMessage = createMessage("assistant", "正在思考中...");
  let finalAnswer = "";

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
          statusText.textContent = "模型正在生成...";
        }

        if (eventData.type === "final") {
          finalAnswer = eventData.content?.trim() || "后端返回了空结果。";
          assistantMessage.paragraph.textContent = finalAnswer;
          statusText.textContent = "响应完成";
        }
      }
    }

    if (!finalAnswer) {
      finalAnswer = assistantMessage.paragraph.textContent.trim() || "后端返回了空结果。";
      assistantMessage.paragraph.textContent = finalAnswer;
    }
  } catch (error) {
    const errorText = `请求失败：${error.message}`;
    assistantMessage.paragraph.textContent = errorText;
    statusText.textContent = "请求失败";
  } finally {
    setSubmitting(false);
  }
});

clearButton.addEventListener("click", () => {
  // 重置 session_id 等于开启一个新的后端会话 thread。
  sessionId = resetSessionId();
  messageList.innerHTML = "";
  renderMessage("assistant", "会话已清空，可以开始新的问题。");
  statusText.textContent = "已清空会话";
});
