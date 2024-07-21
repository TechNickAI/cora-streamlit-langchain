import streamlit as st
from streamlit_local_storage import LocalStorage
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

import os
import json
import arrow
from loguru import logger


for var in ["CORA_COOKIE_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]:
    assert os.environ.get(var), f"Missing required environment variable: {var}"


# Initialize the LocalStorage
local_storage = LocalStorage()

# Set local storage options
storage_key = "google_auth"
storage_expiry_days = 30

# OAuth 2.0 scopes
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
]


def create_flow(state=None):
    logger.debug("Creating OAuth 2.0 flow")
    return Flow.from_client_config(
        client_config={
            "web": {
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=os.environ.get("REDIRECT_URI", "http://localhost:8501/"),
        state=state,
    )


def login():
    logger.debug("Initiating login process")
    flow = create_flow()
    authorization_url, _ = flow.authorization_url(include_granted_scopes="true", access_type="offline")
    st.markdown(f'<a href="{authorization_url}" target="_self">Login with Google</a>', unsafe_allow_html=True)


def callback():
    logger.debug("Handling OAuth 2.0 callback")
    state = st.query_params.get("state")
    flow = create_flow(state=state)
    auth_code = flow.fetch_token(code=st.query_params["code"])
    logger.debug(f"Auth code: {auth_code}")
    st.query_params.clear()

    credentials = flow.credentials
    user_info_service = build(
        serviceName="oauth2",
        version="v2",
        credentials=credentials,
    )
    user_info = user_info_service.userinfo().get().execute()

    logger.debug(f"User info retrieved: {user_info}")
    set_auth_storage(user_info)

    st.rerun()


def logout():
    logger.debug("Logging out user")
    if "user_info" in st.session_state:
        del st.session_state["user_info"]
    local_storage.deleteItem(storage_key)


def set_auth_storage(user_info):
    logger.debug(f"Setting authentication storage for user: {user_info}")
    st.session_state["user_info"] = user_info
    expiry = arrow.now().shift(days=storage_expiry_days)
    storage_data = json.dumps({"user_info": user_info, "expiry": expiry.isoformat()})
    logger.debug(f"Storage data to be set: {storage_data}")
    local_storage.setItem(storage_key, storage_data)
    logger.debug("Storage set successfully")


def get_user_info():
    logger.debug("Retrieving user info from session state or storage")
    if "user_info" in st.session_state:
        logger.debug(f"User info from session state: {st.session_state['user_info']}")
        return st.session_state["user_info"]
    else:
        storage_value = local_storage.getItem(storage_key)
        if storage_value:
            user_data = json.loads(storage_value)
            logger.debug(f"User info from storage: {user_data['user_info']}")
            st.session_state["user_info"] = user_data["user_info"]
            return user_data["user_info"]
        else:
            logger.debug("No user info found in session state or storage")
            return None
