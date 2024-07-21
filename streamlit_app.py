from components.auth import GoogleAuth
from langchain_core.runnables import RunnableConfig
from loguru import logger
from si.agents import create_chat_agent
import streamlit as st
import uuid

# ---------------------------------------------------------------------------- #
#                             Streamlit page set up                            #
# ---------------------------------------------------------------------------- #

ai_logo = "static/logo.png"
# Keep this in sync with static/index.html
st.set_page_config(page_title="Cora: Heart-Centered AI", page_icon=ai_logo, layout="wide")


@st.cache_data()
def get_auth():
    return GoogleAuth()


auth = get_auth()
user_info = auth.get_user_info()
st.header("Cora 🤖 + 💙", divider="rainbow")
if user_info:
    if st.button("Logout"):
        auth.logout()
        st.rerun()

else:
    auth.login_button()


# Handle OAuth callback
if "code" in st.query_params:
    logger.debug("OAuth callback detected with code: {}", st.query_params["code"])
    user_info = auth.callback()
    if user_info:
        st.success("Login successful!")
        st.rerun()


# ----------------------------- Helper functions ----------------------------- #

# TODO convert these to redis
if "chat_history" not in st.session_state:
    logger.debug("Initializing chat_history in session state")
    st.session_state.chat_history = []
if "thread_id" not in st.session_state:
    logger.debug("Initializing thread_id in session state")
    st.session_state.thread_id = str(uuid.uuid4())

# ---------------------------------------------------------------------------- #
#                              Handle the request                              #
# ---------------------------------------------------------------------------- #

# Initialize session state
if "messages" not in st.session_state:
    logger.debug("Initializing messages in session state")
    st.session_state.messages = []

# Display chat messages
if st.session_state.messages:
    logger.debug("Displaying chat messages: {}", st.session_state.messages)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
else:
    logger.debug("No chat messages found, displaying default message")
    with st.chat_message("AI", avatar=ai_logo):
        st.write("Ohai!")

# Create the chat agent
logger.debug("Creating chat agent")


# Get user input
user_request = st.chat_input("How may I assist you today?")

if user_request:
    logger.debug("User input received: {}", user_request)

    agent_executor = create_chat_agent()
    runnable_config = RunnableConfig(configurable={"thread_id": st.session_state.thread_id})

    # Add user message to session state
    st.session_state.messages.append({"role": "human", "content": user_request})

    # Display user message
    with st.chat_message(user_info["given_name"], avatar=user_info["picture"]):
        st.write(user_request)

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
            logger.debug("AI response updated: {}", ai_response)
        else:
            logger.error("Unhandled chunk type: {}", chunk["output"][0]["type"])
            st.error("Unhandled chunk type: %s", chunk["output"][0]["type"])
