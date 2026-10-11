import time
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
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
    padding-bottom: 8px;
    border-bottom: 1px solid #313244;
    margin-bottom: 12px;
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
    height: 150px;
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
    padding: 6px 8px;
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
    st.session_state.transcripts = []

if "suggested_data" not in st.session_state:
    st.session_state.suggested_data = []

# ヘッダー（左上にアプリ名を常時固定）
st.markdown("""
<div class="top-header">
    <div class="app-title">PestSearch AI</div>
    <div class="app-status">● LIVE STREAMING</div>
</div>
""", unsafe_allow_html=True)

# 検索処理関数
def process_text_input(text, search_filename_only):
    if not text.strip():
        return
    
    st.session_state.transcripts.append(text)
    
    if not df_db.empty:
        keywords = text.strip().split()
        hits = []
        for _, row in df_db.iterrows():
            file_name = str(row['file_name'])
            keywords_str = str(row['keywords'])
            
            # 検索対象文字列の判定
            target_str = file_name if search_filename_only else f"{file_name} {keywords_str}"
            
            matched_kws = [kw for kw in keywords if kw.lower() in target_str.lower()]
            if matched_kws:
                hits.append({
                    "id": row['id'],
                    "file_name": row['file_name'],
                    "thumbnail_path": row['thumbnail_path'],
                    "pdf_path": row['pdf_path'],
                    "hit_kw": " / ".join(matched_kws)
                })
        
        if hits:
            st.session_state.suggested_data = hits[:4]

# 左右レイアウト（左 7.5 : 右 2.5）
col_left, col_right = st.columns([7.5, 2.5])

# --- 左カラム：検索オプション ＆ ヒット資料 ---
with col_left:
    st.markdown("<div style='font-size:12px; font-weight:700; color:#A6ADC8;'>MATCHED KNOWLEDGE</div>", unsafe_allow_html=True)
    
    # ファイル名のみ検索対象にするかのチェックボックス
    search_filename_only = st.checkbox("ファイル名のみを検索対象にする（オフ時はキーワード・本文も含める）", value=False)
    st.write("")
    
    if not st.session_state.suggested_data:
        st.markdown("<div style='color:#585B70; font-size:12px; padding-top:40px;'>会話やキーワードから該当するマニュアルがここに表示されます</div>", unsafe_allow_html=True)
    else:
        cols = st.columns(4)
        for idx, item in enumerate(st.session_state.suggested_data):
            with cols[idx]:
                card_html = f"""
                <div class="file-card" title="{item['file_name']} (クリックで参照)">
                    <div class="keyword-tag">MATCH: {item['hit_kw']}</div>
                    <div class="file-name-text">{item['file_name']}</div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
                try:
                    img = Image.open(item['thumbnail_path'])
                    st.image(img, use_container_width=True)
                except:
                    st.markdown('<div class="no-image-box">PREVIEW NO IMAGE</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

# --- 音声入力（URLクエリ経由での受け取りチェック） ---
query_params = st.query_params
if "voice" in query_params:
    voice_text = query_params["voice"]
    st.query_params.clear()
    process_text_input(voice_text, search_filename_only)
    st.rerun()

# --- 右カラム：会話・文字起こしログ ＆ Web Speech API 音声入力 ＆ テキスト入力 ---
with col_right:
    st.markdown("<div style='font-size:12px; font-weight:700; color:#A6ADC8; margin-bottom:6px;'>TRANSCRIPTION LOG</div>", unsafe_allow_html=True)
    
    if st.button("ログ消去", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.suggested_data = []
        st.rerun()

    # 文字起こしログ（固定高エリア）
    log_container = st.container(height=320)
    with log_container:
        if not st.session_state.transcripts:
            st.markdown("<div style='color:#45475A; font-size:11px;'>ログなし</div>", unsafe_allow_html=True)
        else:
            for log in reversed(st.session_state.transcripts):
                st.markdown(f'<div class="log-item">> {log}</div>', unsafe_allow_html=True)

    # 1. HTML5 / Web Speech API によるマイク音声入力コンポーネント
    speech_js = """
    <div style="font-family: sans-serif; background: transparent;">
        <button id="mic-btn" style="width: 100%; padding: 8px; background-color: #1E1E2E; color: #89B4FA; border: 1px solid #313244; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: 0.2s;">
            🎙️ 音声入力を開始 (マイク)
        </button>
        <div id="mic-status" style="color: #7F849C; font-size: 10px; margin-top: 4px; text-align: center;">Chrome / Edge / Safari 対応</div>
    </div>

    <script>
        const btn = document.getElementById('mic-btn');
        const status = document.getElementById('mic-status');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            status.innerText = "※お使いのブラウザは音声認識非対応です";
            btn.disabled = true;
            btn.style.opacity = "0.5";
        } else {
            const recognition = new SpeechRecognition();
            recognition.lang = 'ja-JP';
            recognition.interimResults = false;
            let isListening = false;

            btn.onclick = () => {
                if (isListening) {
                    recognition.stop();
                } else {
                    recognition.start();
                }
            };

            recognition.onstart = () => {
                isListening = true;
                btn.innerText = "🔴 聞き取り中...（発話してください）";
                btn.style.backgroundColor = "#F38BA8";
                btn.style.color = "#11111B";
                status.innerText = "マイクで会話を検出中";
            };

            recognition.onend = () => {
                isListening = false;
                btn.innerText = "🎙️ 音声入力を開始 (マイク)";
                btn.style.backgroundColor = "#1E1E2E";
                btn.style.color = "#89B4FA";
            };

            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                status.innerText = "検出: " + transcript;
                const targetUrl = window.parent.location.pathname + '?voice=' + encodeURIComponent(transcript);
                window.parent.location.href = targetUrl;
            };

            recognition.onerror = (event) => {
                status.innerText = "エラー: " + event.error;
            };
        }
    </script>
    """
    components.html(speech_js, height=65)

    # 2. 手動テキスト / キーワード入力
    if input_text := st.chat_input("キーワード入力..."):
        process_text_input(input_text, search_filename_only)
        st.rerun()
