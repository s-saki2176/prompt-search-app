import streamlit as st
import pandas as pd
from notion_client import Client
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import httpx
import webbrowser

# --- Google OAuth 認証機能 (安定版) ---
def google_auth():
    CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID")
    CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET")
    REDIRECT_URI = st.secrets.get("REDIRECT_URI")
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"
    
    if 'user_info' not in st.session_state:
        query_params = st.query_params
        auth_code = query_params.get("code")

        if not auth_code:
            auth_link = f"{AUTH_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=email%20profile"
            st.markdown(f'<a href="{auth_link}" target="_self">会社のGoogleアカウントでログイン</a>', unsafe_allow_html=True)
            st.stop()
        
        try:
            with httpx.Client() as client:
                token_response = client.post(
                    TOKEN_URL,
                    data={
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET,
                        "code": auth_code,
                        "grant_type": "authorization_code",
                        "redirect_uri": REDIRECT_URI,
                    },
                )
                token_response.raise_for_status()
                access_token = token_response.json()["access_token"]

                user_info_response = client.get(
                    USER_INFO_URL, headers={"Authorization": f"Bearer {access_token}"}
                )
                user_info_response.raise_for_status()
                st.session_state.user_info = user_info_response.json()
                st.query_params.clear()
                st.rerun()

        except Exception as e:
            st.error("認証中にエラーが発生しました。")
            st.error(e)
            st.stop()
            
    user_info = st.session_state.user_info
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN")
    
    if user_info and user_info.get("email", "").endswith(f"@{allowed_domain}"):
        st.sidebar.success(f"{user_info.get('email')}としてログイン中