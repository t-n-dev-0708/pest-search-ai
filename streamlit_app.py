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

# --- カスタムCSS（100%ズーム時のスクロール抑止・デザイン統一） ---
st.markdown("""
<style>
/* 画面全体の縦スクロールを抑止 */
html, body, [data-testid="stAppViewContainer"] {
    height: 100vh;
    overflow: hidden;
    background-color: #11111B;
}

.main .block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 0.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-height: 98vh;
}

/* ヘッダー */
.top-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 6px;
    border-bottom: 1px solid #313244;
    margin-bottom: 8px;
}
.app-title {
    font-size: 18px;
    font-weight: 700;
    color: #CDD6F4;
    letter-spacing: 0.5px;
}
.app-status {
    font-size: 12px;
    color: #A6ADC8;
    background-color: #1E1E2E;
    padding: 3px 8px;
    border-radius: 12px;
    border: 1px solid #313244;
}

/* キーワードグループ見出し */
.kw-group-header {
    font-size: 14px;
    font-weight: 700;
    color: #89B4FA;
    border-left: 4px solid #89B4FA;
    padding-left: 8px;
    margin-top: 10px;
    margin-bottom: 8px;
}

/* プレビューカード（ホバーでズーム） */
.file-card {
    background-color: #1E1E2E;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #313244;
    transition: transform 0.2s ease, border-color 0.2s, box-shadow 0.2s;
}
.file-card:hover {
    transform: scale(1.02);
    border-color: #89B4FA;
    box-shadow: 0 6px 18px rgba(0,0,0,0.4);
}

.no-image-box {
    background-color: #181825;
    height: 110px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    color: #7F849C;
    font-size: 12px;
    font-weight: 600;
    border: 1px dashed #313244;
}

.file-name-text {
    font-size: 13px;
    font-weight: 700;
    color: #CDD6F4;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* 右側ログ表示 */
.log-item {
    font-size: 13px;
    color: #CDD6F4;
    padding: 6px 8px;
    border-bottom: 1px solid #1E1E2E;
    line-height: 1.4;
}

/* 黄色ハイライト */
.highlight-kw {
    background-color: #F9E2AF;
    color: #11111B;
    font-weight: 700;
    padding: 1px 4px;
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

# セッション状態初期化
if "transcripts" not in st.session_state:
    st.session_state.transcripts = []

if "search_filename_only" not in st.session_state:
    st.session_state.search_filename_only = False

if "grouped_results" not in st.session_state:
    st.session_state.grouped_results = {}

# --- 全ログに対する再検索・判定ロジック ---
def recalculate_matches():
    if df_db.empty or not st.session_state.transcripts:
        st.session_state.grouped_results = {}
        return
    
    search_only_fn = st.session_state.search_filename_only
    all_transcripts_text = " ".join(st.session_state.transcripts)

    # DBから検索キーワードの候補を集計
    potential_kws = set()
    for _, row in df_db.iterrows():
        fn = str(row['file_name']).replace('.pdf', '')
        for k in re.split(r'[_ \s]+', fn):
            if len(k.strip()) >= 2:
                potential_kws.add(k.strip())
        
        if not search_only_fn:
            for k in str(row['keywords']).split():
                if len(k.strip()) >= 1:
                    potential_kws.add(k.strip())

    grouped = {}
    for kw in potential_kws:
        if kw.lower() in all_transcripts_text.lower():
            for _, row in df_db.iterrows():
                file_name = str(row['file_name'])
                keywords_str = str(row['keywords'])
                
                # マッチ判定
                is_match = False
                if search_only_fn:
                    if kw.lower() in file_name.lower():
                        is_match = True
                else:
                    if kw.lower() in file_name.lower() or kw.lower() in keywords_str.lower():
                        is_match = True
                        
                if is_match:
                    if kw not in grouped:
                        grouped[kw] = []
                    if not any(f['id'] == row['id'] for f in grouped[kw]):
                        grouped[kw].append({
                            "id": row['id'],
                            "file_name": row['file_name'],
                            "thumbnail_path": row['thumbnail_path'],
                            "pdf_path": row['pdf_path']
                        })
                        
    st.session_state.grouped_results = grouped

def process_text_input(text):
    if not text or not text.strip():
        return
    st.session_state.transcripts.insert(0, text.strip())
    recalculate_matches()

# ヘッダー（常時固定）
st.markdown("""
<div class="top-header">
    <div class="app-title">害虫検索 AI (PestSearch AI)</div>
    <div class="app-status">● リアルタイム会話解析中</div>
</div>
""", unsafe_allow_html=True)

# バックアップ用URLクエリ受取
query_params = st.query_params
if "voice" in query_params:
    voice_text = query_params["voice"]
    st.query_params.clear()
    process_text_input(voice_text)
    st.rerun()

# 左右レイアウト
col_left, col_right = st.columns([7.2, 2.8])

# --- 左カラム：検索オプション ＆ 資料表示 ---
with col_left:
    st.markdown("<div style='font-size:14px; font-weight:700; color:#CDD6F4;'>検出されたナレッジ・資料</div>", unsafe_allow_html=True)
    
    # チェックボックス
    chk_val = st.checkbox(
        "ファイル名のみを検索対象にする", 
        value=st.session_state.search_filename_only,
        key="chk_fn_only"
    )
    
    # チェックボックスの状態変更時に即時再計算
    if chk_val != st.session_state.search_filename_only:
        st.session_state.search_filename_only = chk_val
        recalculate_matches()
        st.rerun()

    if not st.session_state.grouped_results:
        st.markdown("<div style='color:#7F849C; font-size:13px; padding-top:40px; text-align:center;'>右側の会話ログからキーワードが検出されると、ここに該当資料がキーワードごとに分類して表示されます</div>", unsafe_allow_html=True)
    else:
        left_container = st.container(height=520)
        with left_container:
            for kw, files in st.session_state.grouped_results.items():
                st.markdown(f'<div class="kw-group-header">【 {kw} 】に関する資料 ({len(files)}件)</div>', unsafe_allow_html=True)
                cols = st.columns(4)
                for idx, item in enumerate(files):
                    with cols[idx % 4]:
                        card_html = f"""
                        <div class="file-card" title="{item['file_name']}">
                            <div class="file-name-text">{item['file_name']}</div>
                        """
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                        try:
                            img = Image.open(item['thumbnail_path'])
                            st.image(img, use_container_width=True)
                        except Exception:
                            st.markdown('<div class="no-image-box">プレビュー画像なし</div>', unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)

# --- 右カラム：ログ ＆ 音声/手動入力 ---
with col_right:
    st.markdown("<div style='font-size:14px; font-weight:700; color:#CDD6F4; margin-bottom:4px;'>会話・文字起こしログ</div>", unsafe_allow_html=True)
    
    if st.button("ログを全消去", use_container_width=True):
        st.session_state.transcripts = []
        st.session_state.grouped_results = {}
        st.rerun()

    # ハイライト用キーワード集計
    all_registered_kws = set()
    if not df_db.empty:
        for kws in df_db['keywords'].dropna():
            for k in str(kws).split():
                if k.strip(): all_registered_kws.add(k.strip())
        for fn in df_db['file_name'].dropna():
            fn_clean = str(fn).replace('.pdf', '')
            for k in re.split(r'[_ \s]+', fn_clean):
                if len(k.strip()) >= 2: all_registered_kws.add(k.strip())

    # ログ表示（最上部が最新）
    log_container = st.container(height=320)
    with log_container:
        if not st.session_state.transcripts:
            st.markdown("<div style='color:#6C7086; font-size:12px;'>会話ログはまだありません</div>", unsafe_allow_html=True)
        else:
            for log in st.session_state.transcripts:
                display_log = log
                for kw in all_registered_kws:
                    if kw.lower() in display_log.lower():
                        pattern = re.compile(re.escape(kw), re.IGNORECASE)
                        display_log = pattern.sub(f'<span class="highlight-kw">{kw}</span>', display_log)
                
                st.markdown(f'<div class="log-item">▶ {display_log}</div>', unsafe_allow_html=True)

    # 音声認識 JS (セッション切断を防ぐ直接フォーム送信)
    speech_js = """
    <div style="font-family: sans-serif; background: transparent;">
        <button id="mic-btn" style="width: 100%; padding: 8px; background-color: #1E1E2E; color: #89B4FA; border: 1px solid #313244; border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer; transition: 0.2s;">
            🎙️ 音声聞き取りを開始する
        </button>
        <div id="mic-status" style="color: #7F849C; font-size: 11px; margin-top: 4px; text-align: center;">ボタンを押すとマイクで連続自動認識を開始します</div>
    </div>

    <script>
        const btn = document.getElementById('mic-btn');
        const status = document.getElementById('mic-status');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        function sendToStreamlit(text) {
            if (!text) return;
            try {
                const parentDoc = window.parent.document;
                const textarea = parentDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');
                if (textarea) {
                    const nativeSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype, 'value').set;
                    nativeSetter.call(textarea, text);
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    setTimeout(() => {
                        const sendBtn = parentDoc.querySelector('button[data-testid="stChatInputSubmitButton"]');
                        if (sendBtn) {
                            sendBtn.click();
                        } else {
                            textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
                        }
                    }, 100);
                    return;
                }
            } catch (e) { console.log(e); }
            
            const targetUrl = window.parent.location.pathname + '?voice=' + encodeURIComponent(text);
            window.parent.location.href = targetUrl;
        }

        if (!SpeechRecognition) {
            status.innerText = "※お使いのブラウザは音声認識に対応していません";
            btn.disabled = true;
            btn.style.opacity = "0.5";
        } else {
            const recognition = new SpeechRecognition();
            recognition.lang = 'ja-JP';
            recognition.continuous = true;
            recognition.interimResults = false;
            
            let isUserActive = false;

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
                    sendToStreamlit(transcript);
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
    components.html(speech_js, height=70)

    # 手動チャット入力
    if input_text := st.chat_input("手動でキーワードを入力..."):
        process_text_input(input_text)
        st.rerun()
