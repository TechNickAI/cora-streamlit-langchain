from components.auth import GoogleAuth
from langchain_core.runnables import RunnableConfig
from loguru import logger
from si.agents import create_chat_agent
from zep_cloud.client import AsyncZep
from zep_cloud.errors import NotFoundError
import asyncio
import os
import streamlit as st
import uuid

# ---------------------------------------------------------------------------- #
#                             Streamlit page set up                            #
# ---------------------------------------------------------------------------- #

ai_logo = "static/logo.png"
# Keep this in sync with static/index.html
st.set_page_config(page_title="Cora: Heart-Centered AI", page_icon=ai_logo, layout="wide")
st.header("Cora 🤖 + 💙", divider="rainbow")

# Initialize Zep client
zep_api_key = os.getenv("ZEP_API_KEY")
assert zep_api_key, "ZEP_API_KEY environment variable is required."
zep_client = AsyncZep(api_key=zep_api_key)

# Initialize session state
if "chat_history" not in st.session_state:
    logger.debug("Initializing chat_history in session state")
    st.session_state.chat_history = []
if "messages" not in st.session_state:
    logger.debug("Initializing messages in session state")
    st.session_state.messages = []

# ---------------------------------------------------------------------------- #
#                             Handle authentication
# ---------------------------------------------------------------------------- #


async def setup_user():
    auth = GoogleAuth()
    user_info = None
    if "code" in st.query_params:
        logger.debug("OAuth callback detected with code: {}", st.query_params["code"])
        user_info = await auth.callback()
        if user_info:
            st.success("Login successful!")
            st.rerun()

    user_info = auth.get_user_info()
    if user_info:
        if st.button("Logout"):
            auth.logout()
            st.rerun()
    else:
        auth.login_button()

    if user_info:
        # Assert ZEP_API_KEY is set

        # Determine environment

        # Modify email for dev mode
        if os.getenv("APP_ENVIRONMENT", "dev") == "dev":
            user_info["email"] = user_info["email"].replace("@", "+devtest@")

        # Check if user exists in Zep
        try:
            zep_user = await zep_client.user.get(user_info["email"])
        except NotFoundError:
            logger.debug("User not found in Zep, creating new user")
            # Create user in Zep
            zep_user = await zep_client.user.add(
                user_id=user_info["email"],
                email=user_info["email"],
                first_name=user_info["given_name"],
                last_name=user_info["family_name"],
                metadata={"picture": user_info["picture"]},
            )
            user_info["zep_user_id"] = zep_user.id
            logger.debug("Created new user in Zep: {}", zep_user)

    return user_info


user_info = asyncio.run(setup_user())

# ---------------------------------------------------------------------------- #
#                              Handle the request                              #
# ---------------------------------------------------------------------------- #

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

# Get user input
user_request = st.chat_input("How may I assist you today?")

if user_request:
    logger.debug("User input received: {}", user_request)

    # Set up session
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
        zep_client.memory.add_session(
            session_id=st.session_state.thread_id,
            user_id=user_info["email"],
        )

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
