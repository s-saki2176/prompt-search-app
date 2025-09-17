import streamlit as st
import pandas as pd
from notion_client import Client
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from streamlit_oauth import OAuth2Component
import asyncio

# --- Google OAuth認証機能 ---
def check_google_auth():
    CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID")
    CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET")
    REDIRECT_URI = st.secrets.get("REDIRECT_URI")
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    
    if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
        st.error("エラー: Google認証情報がsecrets.tomlに正しく設定されていません。")
        st.stop()

    oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTH_URL, TOKEN_URL, TOKEN_URL, REVOKE_URL)

    if 'token' not in st.session_state:
        result = asyncio.run(oauth2.authorize_button(
            name="会社のGoogleアカウントでログイン",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope="email profile",
            key="google",
            use_container_width=True
        ))
        if result:
            st.session_state.token = result.get('token')
            st.rerun()
        st.stop()
    
    token = st.session_state.get('token')
    user_info = asyncio.run(oauth2.get_user_info(token))
    
    # ★★★ ここにあなたの会社のドメイン名を設定 ★★★
    allowed_domain = "odashima.co.jp" 

    if user_info and user_info.get("email", "").endswith(f"@{allowed_domain}"):
        st.sidebar.success(f"{user_info.get('email')}としてログイン中")
        return True
    else:
        st.error("エラー: 許可されていないドメインのアカウントです。会社のGoogleアカウントでログインしてください。")
        st.session_state.clear()
        st.stop()

# --- メインのアプリケーション ---
def main_app():
    st.title("カエレル内プロンプト検索AI 🐸")
    
    # (APIキー設定は省略)
    
    @st.cache_data(ttl=600)
    def get_prompts_from_notion():
        # ... (先ほど説明したキーワード検索対応版の関数をここに) ...

    # (AI回答生成関数は省略)
    
    # (データ準備とUI部分は省略)


# --- プログラムの実行開始点 ---
if check_google_auth():
    main_app()