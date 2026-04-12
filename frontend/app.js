const messageList = document.getElementById("message-list");
const chatForm = document.getElementById("chat-form");
const queryInput = document.getElementById("query-input");
const apiBaseInput = document.getElementById("api-base");
const statusText = document.getElementById("status-text");
const sendButton = document.getElementById("send-btn");
const clearButton = document.getElementById("clear-btn");

// 前端自己维护一份对话历史，后续每次请求都会把它带给后端。
const history = [];

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
  // 请求发送后禁用输入和按钮，避免重复提交。
  sendButton.disabled = isSubmitting;
  clearButton.disabled = isSubmitting;
  queryInput.disabled = isSubmitting;
  statusText.textContent = isSubmitting ? "正在流式接收后端响应..." : "等待输入";
}

function readSseChunk(buffer) {
  // 后端返回的是 SSE 文本流，每个事件之间用空行 `\n\n` 分隔。
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
  // 阻止浏览器默认表单提交，改为用 JS 发异步请求。
  event.preventDefault();

  const query = queryInput.value.trim();
  if (!query) {
    statusText.textContent = "请输入问题";
    return;
  }

  const apiBase = apiBaseInput.value.trim().replace(/\/$/, "");
  const payload = { query, history };

  renderMessage("user", query);
  history.push({ role: "user", content: query });
  queryInput.value = "";
  setSubmitting(true);

  // 先放一个占位消息，后面随着 SSE 事件到来再更新它。
  const assistantMessage = createMessage("assistant", "正在思考...");
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

        // snapshot 事件表示“生成中”的临时状态。
        if (eventData.type === "snapshot") {
          assistantMessage.paragraph.textContent = eventData.content;
          statusText.textContent = "模型正在生成...";
        }

        // final 事件才是真正要展示并写入历史的最终答案。
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

    history.push({ role: "assistant", content: finalAnswer });
  } catch (error) {
    const errorText = `请求失败：${error.message}`;
    assistantMessage.paragraph.textContent = errorText;
    history.push({ role: "assistant", content: errorText });
    statusText.textContent = "请求失败";
  } finally {
    setSubmitting(false);
  }
});

clearButton.addEventListener("click", () => {
  // 清空前端历史，并把消息列表恢复成初始状态。
  history.length = 0;
  messageList.innerHTML = "";
  renderMessage("assistant", "会话已清空，可以开始新的问题。");
  statusText.textContent = "已清空会话";
});
