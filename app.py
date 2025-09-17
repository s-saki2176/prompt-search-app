import streamlit as st

st.title("これはテスト用アプリです")

st.write("この画面が表示されれば、Streamlitの基本機能は正常に動いています。")

try:
    # 7つあるSecretのうち、1つだけを試しに読み込んでみる
    test_secret = st.secrets["NOTION_API_KEY"]
    st.success("SecretsからNOTION_API_KEYの読み込みに成功しました！")
    
    # 確認のため、読み込んだキーの最初の5文字だけ表示
    st.write(f"読み込んだキーの最初の5文字: {test_secret[:5]}...")

except Exception as e:
    st.error("Secretsの読み込み中にエラーが発生しました。")
    st.error(f"エラーの詳細: {e}")