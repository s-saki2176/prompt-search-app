import streamlit as st
import pandas as pd
from notion_client import Client
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import httpx
import webbrowser

# --- Google OAuth 認証機能 (最終修正版) ---
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
            st.title("カエレルプロンプト検索AI🐸")
            st.write("利用するには、会社のGoogleアカウントでログインしてください。")
            auth_link = f"{AUTH_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=email%20profile"
            st.markdown(f'<a href="{auth_link}" target="_self" style="display: inline-block; padding: 10px 20px; background-color: #4285F4; color: white; text-decoration: none; border-radius: 4px;">会社のGoogleアカウントでログイン</a>', unsafe_allow_html=True)
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
            if st.button("再試行"):
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()
            st.stop()
            
    user_info = st.session_state.user_info
    allowed_domain = st.secrets.get("ALLOWED_DOMAIN")
    
    if user_info and user_info.get("email", "").endswith(f"@{allowed_domain}"):
        st.sidebar.success(f"{user_info.get('email')}としてログイン中")
        if st.sidebar.button("ログアウト"):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
        return True
    else:
        st.error("エラー: 許可されていないドメインのアカウントです。")
        if st.sidebar.button("ログアウト"):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()
        st.stop()

# --- メインのアプリケーション ---
def main_app():
    st.title("カエレルプロンプト検索AI🐸")

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
        model = genai.GenerativeModel('gemini-1.5-flash')
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

    user_query = st.text_input("どのようなプロンプトをお探しですか？")

    if st.button("検索"):
        if user_query:
            with st.spinner("🤖 AIが検索・回答を生成中です..."):
                query_tfidf = vectorizer.transform([user_query])
                cosine_similarities = cosine_similarity(query_tfidf, tfidf_matrix).flatten()
                relevant_indices = [i for i, score in enumerate(cosine_similarities) if score > 0.1]
                sorted_indices = sorted(relevant_indices, key=lambda i: cosine_similarities[i], reverse=True)
                top_indices = sorted_indices[:3]
                relevant_docs = df_prompts.iloc[top_indices]
                answer = generate_answer_with_gemini(user_query, relevant_docs)
                st.markdown("---")
                st.markdown("### 💡 AIからの提案")
                st.markdown(answer)
        else:
            st.warning("質問を入力してください。")

# --- プログラムの実行開始点 ---
if google_auth():
    main_app()