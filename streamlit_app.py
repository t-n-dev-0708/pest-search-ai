import time
import pandas as pd
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(
    page_title="PestSearch AI",
    page_icon="🐛",
    layout="wide",
)

# --- データベース読み込み ---
@st.cache_data
def load_database():
    try:
        return pd.read_csv("database.csv")
    except Exception as e:
        st.error(f"データベースの読み込みに失敗しました: {e}")
        return pd.DataFrame()

df_db = load_database()

# --- 設定サイドバー ---
secrets_api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ 設定")
    if secrets_api_key:
        st.success("🔑 API キー読込完了")
        gemini_api_key = secrets_api_key
    else:
        gemini_api_key = st.text_input("Gemini API キー", type="password")
        st.markdown("[APIキー取得](https://aistudio.google.com/)")
    
    st.divider()
    if st.button("🗑️ 会話をリセット", use_container_width=True):
        st.session_state.messages = []
        st.session_state.retry_trigger = False
        st.rerun()

st.title("🐛 害虫対策ナレッジサジェスト (PestSearch AI)")
st.caption("会話の文脈を読み取り、関連する対策マニュアルや資料を自動で提案します。")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "retry_trigger" not in st.session_state:
    st.session_state.retry_trigger = False

# --- サムネイル・資料の描画関数 ---
def draw_suggested_files(suggested_files):
    if suggested_files.empty:
        return
    
    st.markdown("---")
    st.markdown("💡 **参考資料の提案**")
    
    # 横並びに表示するためのカラムを作成
    cols = st.columns(len(suggested_files))
    
    for idx, row in suggested_files.reset_index().iterrows():
        with cols[idx]:
            # サムネイル表示（ダミー画像がない場合は代替テキスト）
            try:
                img = Image.open(row['thumbnail_path'])
                st.image(img, use_column_width=True, caption=row['file_name'])
            except:
                st.info(f"📄 {row['file_name']}\n(No Image)")
            
            # ダミーPDFへのダウンロードボタン
            try:
                with open(row['pdf_path'], "rb") as f:
                    st.download_button(
                        label="ファイルを開く",
                        data=f,
                        file_name=row['file_name'],
                        mime="application/pdf",
                        key=f"dl_{row['id']}_{time.time()}"
                    )
            except:
                st.button("ファイルを開く", disabled=True, key=f"dl_err_{row['id']}_{time.time()}")

# --- 過去ログの描画 ---
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        if "image" in message and message["image"] is not None:
            st.image(message["image"], width=300)
        if message.get("content"):
            st.markdown(message["content"])
        
        # 過去のサジェストファイルがあれば表示
        if "suggested_files" in message:
            draw_suggested_files(message["suggested_files"])

# --- AI応答・資料検索処理 ---
def process_ai_response(api_key):
    last_user_msg = st.session_state.messages[-1]
    user_text = last_user_msg.get("content", "")
    img_obj = last_user_msg.get("image", None)

    with st.chat_message("assistant", avatar="🤖"):
        try:
            client = genai.Client(api_key=api_key.strip())
            
            # 1. まず通常通りAIに返答を作成させる
            history = []
            for msg in st.session_state.messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                c_text = msg.get("content", "")
                if c_text:
                    history.append(types.Content(role=role, parts=[types.Part.from_text(text=c_text)]))

            contents = []
            if user_text: contents.append(user_text)
            if img_obj: contents.append(img_obj)
            if not contents: contents = ["この画像について説明してください。"]

            chat = client.chats.create(model="gemini-3.8-flash", history=history)
            response_stream = chat.send_message_stream(contents)

            def stream_generator():
                for chunk in response_stream:
                    yield chunk.text

            full_response = st.write_stream(stream_generator())
            
            # 2. キーワード抽出（裏で実行）
            search_prompt = f"""
            以下のユーザーの発言から、データベース検索に役立つ重要なキーワードを「スペース区切り」で抽出してください。
            挨拶、助詞、日常的な会話フレーズは完全に除外し、名詞やトピックだけを出力してください。
            発言: "{user_text}"
            """
            kw_response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=search_prompt
            )
            extracted_keywords = kw_response.text.strip().split()
            
            # 3. CSVデータベースと照合
            suggested_files = pd.DataFrame()
            if extracted_keywords and not df_db.empty:
                # 抽出したキーワードのいずれかが、CSVのkeywords列に含まれているかチェック
                mask = df_db['keywords'].apply(lambda x: any(kw in str(x) for kw in extracted_keywords))
                suggested_files = df_db[mask].head(4) # 最大4件まで
            
            # 4. サジェスト表示
            if not suggested_files.empty:
                draw_suggested_files(suggested_files)
                
            # 履歴に保存
            st.session_state.messages.append({
                "role": "assistant", 
                "content": full_response,
                "suggested_files": suggested_files
            })
            
            st.session_state.retry_trigger = False

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                st.warning("⚠️ 無料枠の上限に達しました。新しいAPIキーを発行してください。")
            if st.button("🔄 もう一度送信する", use_container_width=True):
                st.session_state.retry_trigger = True
                st.rerun()

# --- メインの入力ループ ---
if not gemini_api_key:
    st.info("👈 サイドバーに API キーを入力してください。")
else:
    if prompt := st.chat_input("メッセージを入力（＋ボタンで画像添付）...", accept_file=True, file_type=["png", "jpg", "jpeg"]):
        user_text = prompt.text
        uploaded_files = prompt.files

        img_obj = Image.open(uploaded_files[0]) if uploaded_files else None
        user_msg = {"role": "user", "content": user_text}
        if img_obj: user_msg["image"] = img_obj

        st.session_state.messages.append(user_msg)

        with st.chat_message("user", avatar="👤"):
            if img_obj: st.image(img_obj, width=300)
            if user_text: st.markdown(user_text)

        process_ai_response(gemini_api_key)

    elif st.session_state.retry_trigger and st.session_state.messages:
        process_ai_response(gemini_api_key)
