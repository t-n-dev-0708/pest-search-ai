import time
import pandas as pd
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="PestSearch AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- カスタムCSS（見切れ防止・アバター削除・枠内収容） ---
st.markdown("""
<style>
/* ページ上部の見切れ防止パディング */
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 1rem !important;
}

/* アバターアイコンを完全非表示 */
[data-testid="stChatMessageAvatar"] {
    display: none !important;
}

/* チャットメッセージのスタイル調整 */
[data-testid="stChatMessage"] {
    padding: 8px 12px;
    background-color: #1E1E2E;
    border-radius: 6px;
    margin-bottom: 8px;
}

/* カード内のプレースホルダー */
.no-image-box {
    background-color: #181825;
    height: 130px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    margin-bottom: 8px;
    color: #585B70;
    font-size: 11px;
    border: 1px dashed #313244;
}

/* カード内のファイル名テキスト */
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

/* ボタンの幅をカード内にフィットさせる */
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
st.markdown("<h3 style='margin-bottom:0px; font-size:18px; font-weight:700;'>PestSearch AI</h3>", unsafe_allow_html=True)
st.markdown("<p style='color:#7F849C; font-size:12px; margin-bottom:20px;'>リアルタイム会話分析・資料常時サジェスト</p>", unsafe_allow_html=True)

# 2カラムレイアウト（左7 : 右3）
col_left, col_right = st.columns([7, 3])

# --- 左カラム：検出資料の表示エリア ---
with col_left:
    st.markdown("<span style='font-size:14px; font-weight:600;'>検出資料</span>", unsafe_allow_html=True)
    st.write("")
    
    if st.session_state.latest_suggested.empty:
        st.info("右側の会話からキーワードが検出されると、ここに資料が自動表示されます。")
    else:
        suggested = st.session_state.latest_suggested
        # 4列固定のグリッド配置
        cols = st.columns(4)
        
        for idx, row in suggested.reset_index().iterrows():
            if idx >= 4:
                break
            with cols[idx]:
                # Streamlit標準の枠付きコンテナ内にすべての要素を確実に収める
                with st.container(border=True):
                    # 1. ファイル名
                    st.markdown(f'<span class="file-name-label" title="{row["file_name"]}">{row["file_name"]}</span>', unsafe_allow_html=True)
                    
                    # 2. サムネイル / プレビュー枠
                    try:
                        img = Image.open(row['thumbnail_path'])
                        st.image(img, use_container_width=True)
                    except:
                        st.markdown('<div class="no-image-box">NO PREVIEW</div>', unsafe_allow_html=True)
                    
                    # 3. アクションボタン
                    try:
                        with open(row['pdf_path'], "rb") as f:
                            st.download_button(
                                label="開く",
                                data=f,
                                file_name=row['file_name'],
                                mime="application/pdf",
                                key=f"dl_{row['id']}_{time.time()}_{idx}",
                                use_container_width=True
                            )
                    except:
                        st.button("未準備", disabled=True, key=f"dl_err_{row['id']}_{time.time()}_{idx}", use_container_width=True)

# --- 右カラム：会話ログ・入力エリア ---
with col_right:
    st.markdown("<span style='font-size:14px; font-weight:600;'>会話ログ</span>", unsafe_allow_html=True)
    st.write("")
    
    if st.button("ログ消去", use_container_width=True):
        st.session_state.messages = []
        st.session_state.latest_suggested = pd.DataFrame()
        st.rerun()

    # 固定高（500px）のスクロールエリア
    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # キーワード入力
    if prompt := st.chat_input("会話テキストを入力..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 検索処理
        suggested_files = pd.DataFrame()
        if not df_db.empty and prompt.strip():
            keywords = prompt.strip().split()
            mask = df_db['keywords'].apply(
                lambda x: any(kw.lower() in str(x).lower() for kw in keywords)
            )
            suggested_files = df_db[mask].head(4)
            
            if not suggested_files.empty:
                st.session_state.latest_suggested = suggested_files
                reply_content = f"「{prompt}」から資料を検出しました。"
            else:
                reply_content = f"「{prompt}」に該当する資料はありません。"
        else:
            reply_content = "入力が確認できませんでした。"
            
        st.session_state.messages.append({"role": "assistant", "content": reply_content})
        st.rerun()
