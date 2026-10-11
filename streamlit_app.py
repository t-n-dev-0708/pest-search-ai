import time
import pandas as pd
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="PestSearch AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- カスタムCSS（スクロール抑制・固定レイアウト・ホバー拡大） ---
st.markdown("""
<style>
/* 画面全体の縦スクロールを抑制 */
html, body, [data-testid="stAppViewContainer"] {
    height: 100vh;
    overflow: hidden;
    background-color: #11111B;
}

.main .block-container {
    padding-top: 1rem !important;
    padding-bottom: 0.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-height: 98vh;
}

/* 上部ヘッダー */
.top-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 1px solid #313244;
    margin-bottom: 16px;
}
.app-title {
    font-size: 16px;
    font-weight: 700;
    color: #CDD6F4;
    letter-spacing: 0.5px;
}
.app-status {
    font-size: 11px;
    color: #A6ADC8;
    background-color: #1E1E2E;
    padding: 3px 8px;
    border-radius: 12px;
    border: 1px solid #313244;
}

/* ホバーで少し拡大するファイルカード */
.file-card {
    background-color: #1E1E2E;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #313244;
    transition: transform 0.2s cubic-bezier(0.2, 0, 0, 1), border-color 0.2s, box-shadow 0.2s;
    cursor: pointer;
}
.file-card:hover {
    transform: scale(1.03);
    border-color: #89B4FA;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

/* ヒットキーワードのタグ */
.keyword-tag {
    display: inline-block;
    background-color: #313244;
    color: #89B4FA;
    font-size: 10px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 4px;
    margin-bottom: 6px;
}

/* プレビュー枠 */
.no-image-box {
    background-color: #181825;
    height: 160px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    color: #585B70;
    font-size: 10px;
    border: 1px dashed #313244;
    letter-spacing: 1px;
}

.file-name-text {
    font-size: 12px;
    font-weight: 600;
    color: #CDD6F4;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* 右側ログリスト */
.log-item {
    font-size: 12px;
    color: #BAC2DE;
    padding: 8px 10px;
    border-bottom: 1px solid #1E1E2E;
    font-family: monospace;
}
</style>
""", unsafe_allow_html=True)

# --- データベース読み込み ---
@st.cache_data
def load_database():
    try:
        return pd.read_csv("database.csv")
    except Exception:
        return pd.DataFrame()

df_db = load_database()

# セッション状態の初期化
if "transcripts" not in st.session_state:
    st.session_state.transcripts = [] # 会話ログ（テキストのみ）

if "suggested_data" not in st.session_state:
    st.session_state.suggested_data = [] # ヒット結果 [{file, hit_kw}]

if "is_listening" not in st.session_state:
    st.session_state.is_listening = False

# ヘッダー（左上にアプリ名を常時固定）
st.markdown("""
<div class="top-header">
    <div class="app-title">PestSearch AI</div>
    <div class="app-status">● LIVE STREAMING</div>
</div>
""", unsafe_allow_html=True)

# 左右レイアウト（左 7.5 : 右 2.5）
col_left, col_right = st.columns([7.5, 2.5])

# --- 検索ロジック ---
def process_text_input(text):
    if not text.strip():
        return
    
    # ログに追加
    st.session_state.transcripts.append(text)
    
    # CSVデータベース部分一致検索
    if not df_db.empty:
        keywords = text.strip().split()
        hits = []
        for _, row in df_db.iterrows():
            row_kws = str(row['keywords']).lower()
            matched_kws = [kw for kw in keywords if kw.lower() in row_kws]
            if matched_kws:
                hits.append({
                    "id": row['id'],
                    "file_name": row['file_name'],
                    "thumbnail_path": row['thumbnail_path'],
                    "pdf_path": row['pdf_path'],
                    "hit_kw": " / ".join(matched_kws)
                })
        
        if hits:
            st.session_state.suggested_data = hits[:4] # 最大4件

# --- 左カラム：ヒット資料（ホバープレビュー付きカード） ---
with col_left:
    st.markdown("<div style='font-size:12px; font-weight:700; color:#A6ADC8; margin-bottom:10px;'>MATCHED KNOWLEDGE</div>", unsafe_allow_html=True)
    
    if not st.session_state.suggested_data:
        st.markdown("<div style='color:#585B70; font-size:12px; padding-top:40px;'>会話やキーワードから該当するマニュアルがここに表示されます</div>", unsafe_allow_html=True)
    else:
        cols = st.columns(4)
        for idx, item in enumerate(st.session_state.suggested_data):
            with cols[idx]:
                # カードコンテナ（ホバーでズーム）
                card_html = f"""
                <div class="file-card" title="{item['file_name']} (クリックで参照)">
                    <div class="keyword-tag">MATCH: {item['hit_kw']}</div>
                    <div class="file-name-text">{item['file_name']}</div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
                # 画像またはダミープレビュー
                try:
                    img = Image.open(item['thumbnail_path'])
                    st.image(img, use_container_width=True)
                except:
                    st.markdown('<div class="no-image-box">PREVIEW NO IMAGE</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

# --- 右カラム：会話・文字起こしログ ＆ 音声・キーワード入力 ---
with col_right:
    st.markdown("<div style='font-size:12px; font-weight:700; color:#A6ADC8; margin-bottom:10px;'>TRANSCRIPTION LOG</div>", unsafe_allow_html=True)
    
    # ログクリアボタン
    if st.button("ログ消去", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.suggested_data = []
        st.rerun()

    # 文字起こしログ（固定高エリア）
    log_container = st.container(height=380)
    with log_container:
        if not st.session_state.transcripts:
            st.markdown("<div style='color:#45475A; font-size:11px;'>ログなし</div>", unsafe_allow_html=True)
        else:
            for log in reversed(st.session_state.transcripts):
                st.markdown(f'<div class="log-item">> {log}</div>', unsafe_allow_html=True)

    # 音声入力＆テキスト入力エリア
    st.write("")
    
    # 音声入力トグルボタン（擬似音声ストリーミングUI）
    btn_label = "⏹️ 音声聞き取り停止" if st.session_state.is_listening else "🎙️ 音声入力を開始"
    if st.button(btn_label, use_container_width=True):
        st.session_state.is_listening = not st.session_state.is_listening
        st.rerun()

    if st.session_state.is_listening:
        st.caption("🔴 音声聞き取り中...（キーワードを発話）")

    # 手動テキスト / キーワード入力
    if input_text := st.chat_input("キーワードまたは会話を入力..."):
        process_text_input(input_text)
        st.rerun()
