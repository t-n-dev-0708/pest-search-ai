import time
import pandas as pd
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="PestSearch AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- カスタムCSS（ミニマル化＆レイアウト調整） ---
st.markdown("""
<style>
/* 画面上部の余白を削減 */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
}
/* 左側サジェストカード */
.suggest-card {
    background-color: #1E1E2E;
    border-radius: 6px;
    padding: 12px;
    border: 1px solid #313244;
    margin-bottom: 12px;
}
.no-image-box {
    background-color: #181825;
    height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    margin-bottom: 8px;
    color: #6C7086;
    font-size: 11px;
    border: 1px dashed #45475A;
}
.file-name-label {
    font-size: 12px;
    font-weight: 600;
    color: #CDD6F4;
    margin-bottom: 6px;
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stDownloadButton button, .stButton button {
    width: 100%;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# --- データベース読み込み ---
@st.cache_data
def load_database():
    try:
        return pd.read_csv("database.csv")
    except Exception as e:
        return pd.DataFrame()

df_db = load_database()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "latest_suggested" not in st.session_state:
    st.session_state.latest_suggested = pd.DataFrame()

# ミニマルヘッダー
st.markdown("<h3 style='margin-bottom:0px; font-size:18px;'>PestSearch AI</h3>", unsafe_allow_html=True)
st.markdown("<p style='color:#888; font-size:12px; margin-bottom:15px;'>リアルタイム会話分析・資料常時サジェスト</p>", unsafe_allow_html=True)

# 2カラム構造（左: 広いメインエリア / 右: 縦長会話エリア）
col_left, col_right = st.columns([7, 3])

# --- 左カラム：検出資料の表示エリア ---
with col_left:
    st.markdown("**検出資料**")
    
    if st.session_state.latest_suggested.empty:
        st.info("右側の会話からキーワードが検出されると、ここに資料が自動表示されます。")
    else:
        suggested = st.session_state.latest_suggested
        cols = st.columns(3) # 3列でカードを表示
        
        for idx, row in suggested.reset_index().iterrows():
            col_idx = idx % 3
            with cols[col_idx]:
                st.markdown('<div class="suggest-card">', unsafe_allow_html=True)
                st.markdown(f'<span class="file-name-label" title="{row["file_name"]}">{row["file_name"]}</span>', unsafe_allow_html=True)
                
                try:
                    img = Image.open(row['thumbnail_path'])
                    st.image(img, use_container_width=True)
                except:
                    st.markdown('<div class="no-image-box">PREVIEW NO IMAGE</div>', unsafe_allow_html=True)
                
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

# --- 右カラム：会話ログ・キーワード入力 ---
with col_right:
    st.markdown("**会話ログ**")
    
    if st.button("ログ消去", use_container_width=True):
        st.session_state.messages = []
        st.session_state.latest_suggested = pd.DataFrame()
        st.rerun()

    # 縦長の会話ログ表示エリア（スクロール可能）
    chat_container = st.container(height=480)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # 会話・キーワードの入力欄
    if prompt := st.chat_input("会話テキストを入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # CSVデータベース検索
        suggested_files = pd.DataFrame()
        if not df_db.empty and prompt.strip():
            keywords = prompt.strip().split()
            mask = df_db['keywords'].apply(
                lambda x: any(kw.lower() in str(x).lower() for kw in keywords)
            )
            suggested_files = df_db[mask].head(6)
            
            if not suggested_files.empty:
                st.session_state.latest_suggested = suggested_files
                reply_content = f"「{prompt}」から資料を検出しました。"
            else:
                reply_content = f"「{prompt}」に該当する資料はありません。"
        else:
            reply_content = "入力が確認できませんでした。"
            
        st.session_state.messages.append({"role": "assistant", "content": reply_content})
        st.rerun()
