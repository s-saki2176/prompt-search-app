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
    
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN", "odashima.co.jp")

    if user_info and user_info.get("email", "").endswith(f"@{allowed_domain}"):
        st.sidebar.success(f"{user_info.get('email')}としてログイン中")
        return True
    else:
        st.error("エラー: 許可されていないドメインのアカウントです。会社のGoogleアカウントでログインしてください。")
        st.session_state.clear()
        st.stop()

# --- メインのアプリケーション ---
def main_app():
    st.title("カエレル内プロンプト検索AI🐸")

    NOTION_API_KEY = st.secrets["NOTION_API_KEY"]
    NOTION_DATABASE_ID = st.secrets["NOTION_DATABASE_ID"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

    @st.cache_data(ttl=600)
    def get_prompts_from_notion():
        notion = Client(auth=NOTION_API_KEY)
        results = notion.databases.query(database_id=NOTION_DATABASE_ID).get("results")
        prompts_data = []
        for page in results:
            properties = page.get("properties", {})
            title = properties.get("プロンプト名", {}).get("title", [{}])[0].get("text", {}).get("content", "")
            keywords_list = [tag.get("name", "") for tag in properties.get("関連キーワード", {}).get("multi_select", [])]
            keywords = " ".join(keywords_list)
            page_content = ""
            try:
                blocks = notion.blocks.children.list(block_id=page["id"]).get("results")
                for block in blocks:
                    if block["type"] == "paragraph":
                        page_content += "".join([text["plain_text"] for text in block["paragraph"]["rich_text"]])
            except Exception:
                pass
            search_text = f"{title} {keywords} {page_content}"
            prompts_data.append({
                "title": title,
                "full_text": f"プロンプト名: {title}\n\n---\n\n{page_content}",
                "search_text": search_text
            })
        return pd.DataFrame(prompts_data)

    def generate_answer_with_gemini(query, relevant_prompts):
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerModel('gemini-1.5-flash')
        if relevant_prompts.empty:
            return "申し訳ありませんが、関連するプロンプトが見つかりませんでした。"
        context = "\n\n".join(relevant_prompts['full_text'].tolist())
        prompt_for_gemini = f"""
        あなたは、社内のプロンプト共有をサポートする優秀なアシスタントです。
        以下の参考情報を基にして、ユーザーの質問に最も合うプロンプトを提案してください。
        # ユーザーの質問
        {query}
        # 参考情報
        {context}
        # あなたの回答
        上記の参考情報を踏まえ、プロンプトを1つ選び、なぜ良いかを説明してください。
        その後、選んだプロンプトの全文を、以下の形式で必ず提示してください。
        ---
        ### 提案するプロンプト：[ここにプロンプト名]
        ```
        [ここにプロンプト本文]
        ```
        """
        response = model.generate_content(prompt_for_gemini)
        return response.text

    try:
        df_prompts = get_prompts_from_notion()
        if not df_prompts.empty:
            vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 3))
            tfidf_matrix = vectorizer.fit_transform(df_prompts['search_text'])
    except Exception as e:
        st.error(f"Notionデータ取得エラー: {e}")
        st.stop()

    user_query