import time
import pandas as pd
import streamlit as st
from PIL import Image

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

# --- サイドバー ---
with st.sidebar:
    st.header("⚙️ 設定")
    if st.button("🗑️ 会話をリセット", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("🐛 害虫対策ナレッジサジェスト (PestSearch AI)")
st.caption("入力されたキーワードから関連する対策資料・マニュアルを検索します。")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- サムネイル・資料の描画関数 ---
def draw_suggested_files(suggested_files):
    if suggested_files.empty:
        return
    
    st.markdown("---")
    st.markdown("💡 **参考資料の提案**")
    
    cols = st.columns(min(len(suggested_files), 4))
    
    for idx, row in suggested_files.reset_index().iterrows():
        with cols[idx % 4]:
            try:
                img = Image.open(row['thumbnail_path'])
                st.image(img, use_container_width=True, caption=row['file_name'])
            except:
                st.info(f"📄 {row['file_name']}\n(No Image)")
            
            try:
                with open(row['pdf_path'], "rb") as f:
                    st.download_button(
                        label="ファイルを開く",
                        data=f,
                        file_name=row['file_name'],
                        mime="application/pdf",
                        key=f"dl_{row['id']}_{time.time()}_{idx}"
                    )
            except:
                st.button("ファイルを開く", disabled=True, key=f"dl_err_{row['id']}_{time.time()}_{idx}")

# --- 過去ログの描画 ---
for message in st.session_state.messages:
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        if message.get("content"):
            st.markdown(message["content"])
        if "suggested_files" in message and not message["suggested_files"].empty:
            draw_suggested_files(message["suggested_files"])

# --- チャット入力処理 ---
if prompt := st.chat_input("キーワードを入力してください（例：ゴキブリ、アリ、ユスリカ、料金）..."):
    # ユーザーメッセージを保持
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # CSVデータベースの部分一致検索
    suggested_files = pd.DataFrame()
    if not df_db.empty and prompt.strip():
        keywords = prompt.strip().split()
        mask = df_db['keywords'].apply(
            lambda x: any(kw.lower() in str(x).lower() for kw in keywords)
        )
        suggested_files = df_db[mask].head(4)

    # 応答メッセージと表示データ作成
    if not suggested_files.empty:
        reply_content = f"「**{prompt}**」に関する資料が見つかりました。"
    else:
        reply_content = f"「**{prompt}**」に該当する資料は見つかりませんでした。（登録キーワード: ゴキブリ, アリ, ユスリカ, 料金）"

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply_content,
        "suggested_files": suggested_files
    })
    st.rerun()
