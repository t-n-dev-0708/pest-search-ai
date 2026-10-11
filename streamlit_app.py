import time
import re
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(
    page_title="PestSearch AI",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- カスタムCSS（日本語化・文字拡大・スクロール抑制・ハイライト） ---
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
    font-size: 20px;
    font-weight: 700;
    color: #CDD6F4;
    letter-spacing: 0.5px;
}
.app-status {
    font-size: 13px;
    color: #A6ADC8;
    background-color: #1E1E2E;
    padding: 4px 10px;
    border-radius: 12px;
    border: 1px solid #313244;
}

/* 検索結果カード（ホバーで拡大） */
.file-card {
    background-color: #1E1E2E;
    border-radius: 8px;
    padding: 12px;
    border: 1px solid #313244;
    transition: transform 0.2s ease, border-color 0.2s, box-shadow 0.2s;
}
.file-card:hover {
    transform: scale(1.03);
    border-color: #89B4FA;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}

/* 一致キーワードのタグ */
.keyword-tag {
    display: inline-block;
    background-color: #313244;
    color: #89B4FA;
    font-size: 12px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
}

/* プレビュー画像枠 */
.no-image-box {
    background-color: #181825;
    height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    color: #7F849C;
    font-size: 13px;
    font-weight: 600;
    border: 1px dashed #313244;
}

.file-name-text {
    font-size: 14px;
    font-weight: 700;
    color: #CDD6F4;
    margin-bottom: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* 右側ログ表示 */
.log-item {
    font-size: 14px;
    color: #CDD6F4;
    padding: 8px 10px;
    border-bottom: 1px solid #1E1E2E;
    line-height: 1.5;
}

/* 黄色ハイライト表示 */
.highlight-kw {
    background-color: #F9E2AF;
    color: #11111B;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
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
    st.session_state.transcripts = [] # 会話ログリスト

if "suggested_data" not in st.session_state:
    st.session_state.suggested_data = [] # ヒットした資料データ

# ヘッダー（常時固定）
st.markdown("""
<div class="top-header">
    <div class="app-title">害虫検索 AI (PestSearch AI)</div>
    <div class="app-status">● リアルタイム解析中</div>
</div>
""", unsafe_allow_html=True)

# テキスト解析 & 検索ロジック
def process_text_input(text, search_filename_only):
    if not text.strip():
        return
    
    # ログの一番最初（最上部）に追加
    st.session_state.transcripts.insert(0, text)
    
    if not df_db.empty:
        # 入力テキストを分かち書き/スペース分割
        words = text.strip().split()
        hits = []
        for _, row in df_db.iterrows():
            file_name = str(row['file_name'])
            keywords_str = str(row['keywords'])
            
            target_str = file_name if search_filename_only else f"{file_name} {keywords_str}"
            
            matched_kws = [w for w in words if w.lower() in target_str.lower()]
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

# 左右レイアウト（左 7.2 : 右 2.8）
col_left, col_right = st.columns([7.2, 2.8])

# --- 左カラム：検索オプション ＆ ヒット資料表示 ---
with col_left:
    st.markdown("<div style='font-size:15px; font-weight:700; color:#CDD6F4; margin-bottom:4px;'>検出されたナレッジ・資料</div>", unsafe_allow_html=True)
    
    search_filename_only = st.checkbox("ファイル名のみを検索対象にする", value=False)
    st.write("")
    
    if not st.session_state.suggested_data:
        st.markdown("<div style='color:#7F849C; font-size:14px; padding-top:50px; text-align:center;'>会話ログからキーワードが検出されると、ここに該当資料が表示されます</div>", unsafe_allow_html=True)
    else:
        cols = st.columns(4)
        for idx, item in enumerate(st.session_state.suggested_data):
            with cols[idx]:
                card_html = f"""
                <div class="file-card" title="{item['file_name']}">
                    <div class="keyword-tag">一致キーワード: {item['hit_kw']}</div>
                    <div class="file-name-text">{item['file_name']}</div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
                try:
                    img = Image.open(item['thumbnail_path'])
                    st.image(img, use_container_width=True)
                except:
                    st.markdown('<div class="no-image-box">プレビュー画像なし</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

# --- 音声入力データ受け取り（クエリパラメータ経由） ---
query_params = st.query_params
if "voice" in query_params:
    voice_text = query_params["voice"]
    st.query_params.clear()
    process_text_input(voice_text, search_filename_only)
    st.rerun()

# --- 右カラム：会話・文字起こしログ ＆ 音声/キー入力 ---
with col_right:
    st.markdown("<div style='font-size:15px; font-weight:700; color:#CDD6F4; margin-bottom:6px;'>会話・文字起こしログ</div>", unsafe_allow_html=True)
    
    if st.button("ログを全消去", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.suggested_data = []
        st.rerun()

    # DB内の全登録キーワードを取得（ログのハイライト用）
    all_registered_kws = set()
    if not df_db.empty:
        for kws in df_db['keywords'].dropna():
            for k in str(kws).split():
                if k.strip():
                    all_registered_kws.add(k.strip())

    # 会話ログエリア（固定高でスクロール）
    log_container = st.container(height=310)
    with log_container:
        if not st.session_state.transcripts:
            st.markdown("<div style='color:#6C7086; font-size:13px;'>会話ログはまだありません</div>", unsafe_allow_html=True)
        else:
            # 最新のログから順（最上部）に表示
            for log in st.session_state.transcripts:
                display_log = log
                # 登録キーワードに一致する単語があれば黄色くハイライト置換
                for kw in all_registered_kws:
                    if kw.lower() in display_log.lower():
                        pattern = re.compile(re.escape(kw), re.IGNORECASE)
                        display_log = pattern.sub(f'<span class="highlight-kw">{kw}</span>', display_log)
                
                st.markdown(f'<div class="log-item">▶ {display_log}</div>', unsafe_allow_html=True)

    # 1. 常時マイク音声認識 Web Speech API コンポーネント
    speech_js = """
    <div style="font-family: sans-serif; background: transparent;">
        <button id="mic-btn" style="width: 100%; padding: 10px; background-color: #1E1E2E; color: #89B4FA; border: 1px solid #313244; border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer; transition: 0.2s;">
            🎙️ 音声聞き取りを開始する
        </button>
        <div id="mic-status" style="color: #7F849C; font-size: 11px; margin-top: 4px; text-align: center;">ボタンを押すとマイクで連続自動認識を開始します</div>
    </div>

    <script>
        const btn = document.getElementById('mic-btn');
        const status = document.getElementById('mic-status');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            status.innerText = "※お使いのブラウザは音声認識に対応していません";
            btn.disabled = true;
            btn.style.opacity = "0.5";
        } else {
            const recognition = new SpeechRecognition();
            recognition.lang = 'ja-JP';
            recognition.continuous = true; // 連続認識モード
            recognition.interimResults = false;
            
            let isUserActive = false; // ユーザーが明示的にONにしたか

            btn.onclick = () => {
                if (isUserActive) {
                    isUserActive = false;
                    recognition.stop();
                    btn.innerText = "🎙️ 音声聞き取りを開始する";
                    btn.style.backgroundColor = "#1E1E2E";
                    btn.style.color = "#89B4FA";
                    status.innerText = "音声認識を停止しました";
                } else {
                    isUserActive = true;
                    try { recognition.start(); } catch(e){}
                    btn.innerText = "🔴 聞き取り中... (クリックで停止)";
                    btn.style.backgroundColor = "#F38BA8";
                    btn.style.color = "#11111B";
                    status.innerText = "会話を常時聞き取り中...";
                }
            };

            // 無音などでブラウザが勝手に終了した場合でも、ユーザーがOFFにするまで再開し続ける
            recognition.onend = () => {
                if (isUserActive) {
                    try { recognition.start(); } catch(e){}
                }
            };

            recognition.onresult = (event) => {
                const lastIndex = event.results.length - 1;
                const transcript = event.results[lastIndex][0].transcript.trim();
                if (transcript) {
                    status.innerText = "検出: " + transcript;
                    const targetUrl = window.parent.location.pathname + '?voice=' + encodeURIComponent(transcript);
                    window.parent.location.href = targetUrl;
                }
            };

            recognition.onerror = (event) => {
                if (event.error !== 'no-speech') {
                    status.innerText = "エラー: " + event.error;
                }
            };
        }
    </script>
    """
    components.html(speech_js, height=75)

    # 2. 手動テキスト / キーワード入力欄
    if input_text := st.chat_input("手動でキーワードを入力..."):
        process_text_input(input_text, search_filename_only)
        st.rerun()
