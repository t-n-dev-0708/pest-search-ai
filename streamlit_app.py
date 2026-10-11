import time
import pandas as pd
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="PestSearch AI",
    layout="wide",
)

# --- カスタムCSS（アイコン削除＆カードサイズ固定） ---
st.markdown("""
<style>
/* サジェストエリア枠 */
.suggest-container {
    background-color: #1E1E2E;
    border-radius: 8px;
    padding: 16px;
    margin-top: 12px;
    margin-bottom: 16px;
    border: 1px solid #313244;
}
/* No Imageのプレースホルダー（高さ固定） */
.no-image-box {
    background-color: #181825;
    height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    margin-bottom: 8px;
    color: #A6ADC8;
    font-size: 13px;
    border: 1px dashed #45475A;
}
/* ファイル名ラベル（一列で省略表示） */
.file-name-label {
    font-size: 13px;
    font-weight: 600;
    color: #CDD6F4;
    margin-bottom: 8px;
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
/* ボタンサイズ統一 */
.stDownloadButton button, .stButton button {
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

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
    st.header("設定")
    if st.button("会話をリセット", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("害虫対策ナレッジサジェスト (PestSearch AI)")
st.caption("入力されたキーワードから関連する対策資料・マニュアルを検索します。")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- サムネイル・資料の描画関数（サイズ固定版） ---
def draw_suggested_files(suggested_files):
    if suggested_files.empty:
        return
    
    st.markdown('<div class="suggest-container">', unsafe_allow_html=True)
    st.markdown("**参考資料**")
    
    # 常に4列固定にすることで、件数によってカード幅が変動するのを防ぐ
    cols = st.columns(4)
    
    for idx, row in suggested_files.reset_index().iterrows():
        if idx >= 4:
            break
        with cols[idx]:
            # ファイル名
            st.markdown(f'<span class="file-name-label" title="{row["file_name"]}">{row["file_name"]}</span>', unsafe_allow_html=True)
            
            # サムネイル表示（固定枠）
            try:
                img = Image.open(row['thumbnail_path'])
                st.image(img, use_container_width=True)
            except:
                st.markdown('<div class="no-image-box">PREVIEW NO IMAGE</div>', unsafe_allow_html=True)
            
            # ダウンロードボタン
            try:
                with open(row['pdf_path'], "rb") as f:
                    st.download_button(
                        label="ファイルを開く",
                        data=f,
                        file_name=row['file_name'],
                        mime="application/pdf",
                        key=f"dl_{row['id']}_{time.time()}_{idx}",
                        use_container_width=True
                    )
            except:
                st.button("ファイルなし", disabled=True, key=f"dl_err_{row['id']}_{time.time()}_{idx}", use_container_width=True)
                
    st.markdown('</div>', unsafe_allow_html=True)

# --- 過去ログの描画（アバターの絵文字を排除） ---
for message in st.session_state.messages:
    avatar_val = "user" if message["role"] == "user" else "assistant"
    with st.chat_message(message["role"]):
        if message.get("content"):
            st.markdown(message["content"])
        if "suggested_files" in message and not message["suggested_files"].empty:
            draw_suggested_files(message["suggested_files"])

# --- チャット入力処理 ---
if prompt := st.chat_input("キーワードを入力してください（例：ゴキブリ、アリ、ユスリカ、料金）..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    suggested_files = pd.DataFrame()
    if not df_db.empty and prompt.strip():
        keywords = prompt.strip().split()
        mask = df_db['keywords'].apply(
            lambda x: any(kw.lower() in str(x).lower() for kw in keywords)
        )
        suggested_files = df_db[mask].head(4)

    if not suggested_files.empty:
        reply_content = f"「**{prompt}**」に関する検索結果を表示します。"
    else:
        reply_content = f"「**{prompt}**」に該当する資料は見つかりませんでした。（登録キーワード: ゴキブリ, アリ, ユスリカ, 料金）"

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply_content,
        "suggested_files": suggested_files
    })
    st.rerun()
