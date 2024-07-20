from langchain_core.runnables import RunnableConfig
from si.agents import create_chat_agent
import streamlit as st
import uuid

# ---------------------------------------------------------------------------- #
#                             Streamlit page set up                            #
# ---------------------------------------------------------------------------- #

ai_logo = "static/logo.png"
# Keep this in sync with static/index.html
st.set_page_config(page_title="Cora: Heart-Centered AI", page_icon=ai_logo, layout="wide")

st.header("Cora 🤖 + 💙", divider="rainbow")

# ----------------------------- Helper functions ----------------------------- #

# TODO convert these to redis
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


# ---------------------------------------------------------------------------- #
#                              Handle the request                              #
# ---------------------------------------------------------------------------- #

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
if st.session_state.messages:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
else:
    with st.chat_message("AI", avatar=ai_logo):
        st.write("Ohai!")


# Create the chat agent
agent_executor = create_chat_agent()
runnable_config = RunnableConfig(configurable={"thread_id": st.session_state.thread_id})

# Get user input
user_request = st.chat_input("How may I assist you today?")
if user_request:
    # Add user message to session state
    st.session_state.messages.append({"role": "human", "content": user_request})

    # Display user message
    with st.chat_message("human"):
        st.write(user_request)

    # Create a placeholder for the AI response
    ai_placeholder = st.empty()

    ai_response = ""
    for chunk in agent_executor.stream({"input": user_request}, config=runnable_config):
        # The top level response will either be agent or tool_call
        if chunk["output"][0]["type"] == "text":
            ai_response += chunk["output"][0]["text"]
            # Update the placeholder with the current response
            with st.chat_message("AI", avatar=ai_logo):
                st.write(ai_response)

            # Add AI message to session state
            st.session_state.messages.append({"role": "ai", "content": ai_response})
        else:
            st.error("Unhandled chunk type: %s", chunk["output"][0]["type"])
