import time

import streamlit as st

from agent.react_agent import ReactAgent


# 页面标题。
st.title("智能扫通机器人智能客服")
st.divider()

# 首次进入页面时，在当前 Streamlit 会话中创建一个 Agent 实例。
# session_state 是 Streamlit 的会话级状态容器，
# 同一个用户在这个会话里的多轮对话会共享这里的数据。
if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

# message 用来保存当前会话中的聊天记录。
# 这份数据既负责页面回显，也负责为 Agent 提供短期记忆。
if "message" not in st.session_state:
    st.session_state["message"] = []

# 每次脚本重新运行时，都把历史聊天记录重新渲染出来。
# 这是 Streamlit 聊天应用的常见写法。
for message in st.session_state["message"]:
    st.chat_message(message["role"]).write(message["content"])

# 用户输入框。
prompt = st.chat_input()

if prompt:
    # 先把用户这一轮输入显示到界面。
    st.chat_message("user").write(prompt)

    # 这里先复制一份“当前轮提问之前”的历史消息。
    # 这是本次短期记忆改造里最关键的一步之一。
    #
    # 为什么要先 copy 再 append？
    # 因为 execute_stream 会单独接收 query 参数。
    # 如果先把 prompt append 到 message，再把整个 message 当 history 传进去，
    # 那么当前这句用户输入会出现两次：
    # 1. 一次在 history 里
    # 2. 一次在 query 里
    # 这会导致模型输入重复。
    #
    # 所以正确顺序是：
    # 1. 先复制旧历史 history
    # 2. 再把当前 prompt 追加到 session_state["message"] 里
    # 3. 调用 execute_stream(prompt, history=history)
    history = st.session_state["message"].copy()

    # 把当前轮用户输入追加到会话记录中。
    # 这样页面刷新后仍然能看到这条消息，
    # 同时下一轮对话时它也会成为候选历史消息的一部分。
    st.session_state["message"].append({"role": "user", "content": prompt})

    # 保存本轮 assistant 流式输出的所有片段。
    # 最终会把完整回复再写回到 session_state["message"]。
    response_messages = []
    with st.spinner("智能客服思考中..."):
        # 调用 Agent，并把“当前轮之前的历史”作为短期记忆传入。
        # 原来这里只传 prompt，所以模型每轮都会失去上下文。
        res_stream = st.session_state["agent"].execute_stream(prompt, history=history)

        def capture(generator, cache_list):
            """
            包装流式输出生成器。

            作用：
            1. 从 Agent 持续获取新的输出片段；
            2. 把这些片段缓存到 cache_list 中；
            3. 再逐字符返回给 Streamlit，形成“打字机效果”。
            """
            for chunk in generator:
                # 缓存整段输出，便于最后拼接出完整回复。
                cache_list.append(chunk)

                # 逐字符输出到前端，让显示更自然。
                for char in chunk:
                    time.sleep(0.01)
                    yield char

        # 将 assistant 的流式回复显示在聊天窗口中。
        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))

        # 把 assistant 的最终回复写回聊天记录。
        # 这样下一轮调用时，这条回复也会进入短期记忆窗口。
        st.session_state["message"].append({"role": "assistant", "content": response_messages[-1]})

        # 重新运行页面脚本，确保状态与展示同步。
        st.rerun()
