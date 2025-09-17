import streamlit as st
from streamlit_oauth import OAuth2Component
# asyncioは不要なので削除

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
    # ★★★ asyncio.run() を削除 ★★★
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
        st.rerun()
else:
    token = st.session_state.get('token')
    # ★★★ asyncio.run() を削除 ★★★
    user_info = oauth2.get_user_info(token)
    
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN")

    if user_info and user_info.get("email", "").endswith(f"@{allowed_domain}"):
        st.success("認証に成功しました！")
        st.write(f"{user_info.get('email')}としてログインしています。")
    else:
        st.error("エラー: 許可されていないドメインのアカウントです。")
        if st.button("ログアウト"):
            # セッション情報をクリアして、再度ログインボタンを表示
            st.session_state.clear()
            st.rerun()