import streamlit as st
import pandas as pd
from notion_client import Client
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- パスワード認証機能 ---
def check_password():
    try:
        correct_password = st.secrets["APP_PASSWORD"]
    except FileNotFoundError:
        st.error("エラー: .streamlit/secrets.toml ファイルが見つかりません。")
        st.stop()
    except KeyError:
        st.error("エラー: secrets.toml に APP_PASSWORD を設定してください。")
        st.stop()

    password = st.text_input("パスワードを入力してください", type="password")

    if not password:
        st.stop()

    if password == correct_password:
        return True
    else:
        st.error("パスワードが違います。")
        st.stop()

# --- メインのアプリケーション ---
def main_app():
    st.title("部署内プロンプト検索AI 🚀")

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
        model = genai.GenerativeModel('gemini-2.0-flash-lite')
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
if check_password():
    main_app()