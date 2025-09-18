import streamlit as st
from streamlit_oauth import OAuth2Component

st.title("Google認証テスト")

# --- Google OAuth認証機能 ---
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
    result = oauth2.authorize_button(
        name="会社のGoogleアカウントでログイン",
        icon="https://www.google.com/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope="email profile",
        key="google",
        use_container_width=True
    )
    if result:
        st.session_state.token = result.get('token')
        st.session_state.user_info = result.get('token', {}).get('userinfo')
        st.rerun()
else:
    user_info = st.session_state.get('user_info')
    
    # ★★★ デバッグ用：取得したユーザー情報を画面に表示 ★★★
    st.write("---")
    st.write("Googleから取得したユーザー情報:")
    st.json(user_info) # user_infoの内容をすべて表示
    st.write("---")
    
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN")

    if user_info and user_info.get("email", "").endswith(f"@{allowed_domain}"):
        st.success("認証に成功しました！")
        st.write(f"{user_info.get('email')}としてログインしています。")
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()
    else:
        st.error("エラー: 許可されていないドメインのアカウントです。")
        if st.button("ログアウト"):
            st.session_state.clear()
            st.rerun()