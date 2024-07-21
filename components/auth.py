from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from loguru import logger
from streamlit_local_storage import LocalStorage
import json
import os
import streamlit as st


class GoogleAuth:
    def __init__(self):
        # Ensure required environment variables are set
        required_vars = ["CORA_COOKIE_SECRET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise OSError(f"Missing required environment variables: {', '.join(missing_vars)}")

        self.storage_key = "cora_google_auth"
        self.storage_expiry_days = 30
        self.scopes = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
        ]

    @property
    def local_storage(self):
        if not hasattr(self, "_local_storage"):
            self._local_storage = LocalStorage()
        return self._local_storage

    def create_flow(self, state=None):
        return Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                    "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=self.scopes,
            redirect_uri=os.environ.get("REDIRECT_URI", "http://localhost:8501/"),
            state=state,
        )

    def login_button(self):
        flow = self.create_flow()
        authorization_url, _ = flow.authorization_url(include_granted_scopes="true", access_type="offline")
        st.link_button(
            label="Login with Google",
            url=authorization_url,
            type="primary",
        )

    def callback(self):
        logger.debug("Handling OAuth 2.0 callback")
        state = st.query_params.get("state")
        flow = self.create_flow(state=state)
        try:
            flow.fetch_token(code=st.query_params["code"])
        except Exception as e:
            logger.error(f"Error fetching token: {e}")
            st.error("Authentication failed. Please try again.")
            return None

        st.query_params.clear()

        credentials = flow.credentials
        try:
            user_info_service = build(
                serviceName="oauth2",
                version="v2",
                credentials=credentials,
            )
            user_info = user_info_service.userinfo().get().execute()
        except Exception as e:
            logger.error(f"Error retrieving user info: {e}")
            st.error("Failed to retrieve user information. Please try again.")
            return None

        logger.debug(f"User info retrieved: {user_info}")
        self.set_auth_storage(user_info)
        return user_info

    def logout(self):
        logger.debug("Logging out user")
        self.local_storage.deleteItem(self.storage_key)
        st.session_state["user_info"] = None

    def set_auth_storage(self, user_info):
        logger.debug(f"Setting authentication storage for user: {user_info}")
        storage_data = json.dumps({"user_info": user_info})
        st.session_state["user_info"] = storage_data
        self.local_storage.setItem(self.storage_key, storage_data)

    def get_user_info(self):
        storage_value = st.session_state.get("user_info") or self.local_storage.getItem(self.storage_key)

        if storage_value:
            user_data = json.loads(storage_value)
            logger.debug(f"User info: {user_data['user_info']}")
            return user_data["user_info"]
        else:
            logger.debug("No user info found")
            return None
