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

# セッションにトークンとユーザー情報がない場合、ログインボタンを表示
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
        # ★★★ 修正点：ログイン成功時にユーザー情報も一緒に保存する ★★★
        st.session_state.token = result.get('token')
        st.session_state.user_info = result.get('token', {}).get('userinfo') # ユーザー情報を取得
        st.rerun()

# セッションにユーザー情報がある場合、認証済みとみなす
else:
    user_info = st.session_state.get('user_info')
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