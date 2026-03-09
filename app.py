# claude 2026/3/2 book-Reader App4
import gradio as gr
import requests
import re
import json
import os

# [保留原有的 Google Drive 與 JSON 讀取工具函數...]
def extract_drive_file_id(text):
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", text): return text
    patterns = [r'/d/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)']
    for p in patterns:
        m = re.search(p, text)
        if m: return m.group(1)
    return None

def download_drive_text(text):
    file_id = extract_drive_file_id(text)
    if not file_id: return " ❌ 無法解析連結或ID"
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(url)
    return r.content.decode("utf-8") if r.status_code == 200 else " ❌ 下載失敗"

def load_local_json():
    if os.path.exists("stories.json"):
        with open("stories.json", "r", encoding="utf-8") as f: return json.load(f)
    return {}

def load_drive_json(text):
    try: return json.loads(download_drive_text(text))
    except: return {}

def get_story_list(data): return [(data[k]["title"], k) for k in data]
def get_chapter_list(data, story_key):
    if story_key in data:
        chapters = data[story_key]["chapters"]
        return [(chapters[c], c) for c in chapters]
    return []

def format_paragraphs(text):
    return "".join([f'<div class="paragraph">{p}</div>' for p in text.split("\n") if p.strip()])

# =========================
# UI 介面
# =========================

with gr.Blocks(css="""
.highlight { background:#ffcc00; font-weight:bold; border-radius:4px; padding:2px; }
.paragraph { margin-bottom:12px; font-size:18px; line-height:1.6; transition: all 0.3s; }
.fav-btn { width: 100%; text-align: left; padding: 8px; margin-bottom: 4px; cursor: pointer; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9; }
.fav-btn:hover { background: #eee; }
.hidden-el { display: none !important; }
.novel-box { height: 70vh; overflow-y: auto; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background: #fafafa;}
#voice_selector_container select { width: 100%;padding: 8px;border: 1px solid #ddd;border-radius: 4px;font-size: 14px;background: white;}
.tab-nav button { font-size: 16px !important; padding: 12px !important; }
/* 按鈕列 */
.btn-row {display: flex;flex-direction: row !important;gap: 4px;margin-bottom: 8px;}
.btn-row > * {flex: 1;min-width: 0;}
/* 文字方塊高度 - 電腦版 */
.novel-box {height: 75vh;overflow-y: auto;border: 1px solid #ddd;border-radius: 8px;padding: 16px;background: #fafafa;}
/* 手機版 */
@media (max-width: 768px) {
    .novel-box {height: 60vh !important;}
    /* 標題縮小 */
    h1 { font-size: 16px !important; margin: 4px 0 !important; }
    /* 按鈕文字縮小 */
    .btn-row button { font-size: 13px !important; padding: 6px 4px !important; }
}
""") as app:

    DEFAULT_JSON_ID = "1WrNyH65rrX9NN_hr20xL6uDZpydycA46"

    def update_title(story_key, chapter_key, data):
        story = data.get(story_key, {}).get("title", "書籍")
        chapters = data.get(story_key, {}).get("chapters", {})
        chapter = chapters.get(chapter_key, "章節")
        return f"# 小說閱讀器：{story} - {chapter}"

    def load_default_json():
        local = load_local_json()
        if local:
            return local
        return load_drive_json(DEFAULT_JSON_ID)

    story_data = gr.State(load_default_json())

    # ── Toast JS 片段（共用）──────────────────────────────────────────
    TOAST_JS_GREEN = """
        let toast = document.createElement("div");
        toast.innerText = "✅ 內容已載入，可以開始閱讀！";
        toast.style.cssText = `
            position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
            background: #4caf50; color: white; padding: 12px 24px;
            border-radius: 8px; font-size: 16px; z-index: 9999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: opacity 1s ease;
        `;
        document.body.appendChild(toast);
        setTimeout(() => { toast.style.opacity = "0"; }, 2500);
        setTimeout(() => { toast.remove(); }, 3500);
    """

    TOAST_JS_ORANGE = """
        let toast = document.createElement("div");
        toast.innerText = "⭐ 最愛章節已載入，可以開始閱讀！";
        toast.style.cssText = `
            position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
            background: #ff9800; color: white; padding: 12px 24px;
            border-radius: 8px; font-size: 16px; z-index: 9999;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: opacity 1s ease;
        `;
        document.body.appendChild(toast);
        setTimeout(() => { toast.style.opacity = "0"; }, 2500);
        setTimeout(() => { toast.remove(); }, 3500);
    """

    with gr.Tabs(elem_id="main_tabs") as tabs:

        # ===== 閱讀畫面 =====
        with gr.Tab(" 📖 閱讀", id="read_tab"):
            title_display = gr.Markdown("# 小說閱讀器：書籍 - 章節")

            # 頂部控制列
            with gr.Row(elem_classes=["btn-row"]):
                to_setting_btn = gr.Button(" ⚙ 設定", scale=1)
                play_btn = gr.Button(" ▶ 播放", scale=2, variant="primary")
                pause_btn = gr.Button(" ⏸ 暫停", scale=2)
                stop_btn = gr.Button(" ⏹ 停止", scale=2)

            html_display = gr.HTML(elem_id="novel_content", elem_classes=["novel-box"])

        # ===== 設定畫面 =====
        with gr.Tab(" ⚙ 設定", id="setting_tab"):
            gr.Markdown("## 📚 書籍選單")
            story_dropdown = gr.Dropdown(label="選擇書籍")
            chapter_dropdown = gr.Dropdown(label="選擇章節")

            with gr.Row():
                load_btn = gr.Button("匯入內容", variant="primary")
                to_read_btn = gr.Button(" 📖 前往閱讀")

            gr.Markdown("## 📂 匯入JSON")
            json_input = gr.Textbox(label="JSON網址或ID")
            json_btn = gr.Button("載入JSON")

            gr.Markdown("## 🎧 語音設定")
            voice_display = gr.HTML(elem_id="voice_selector_container", value="")
            voice_value = gr.Textbox(visible=True, elem_classes=["hidden-el"], elem_id="voice_value")
            voice_dropdown = gr.Dropdown(label="音色", choices=[], value=None)
            pitch = gr.Slider(0.5, 2, 1, label="音高")
            rate = gr.Slider(0.5, 2, 1, label="語速")
            font_size = gr.Slider(12, 32, 18, step=1, label="字體大小")

            gr.Markdown("## ⭐ 我的最愛")
            favorites_html = gr.HTML(elem_id="fav_list")

            # 隱藏元件
            fav_id_input = gr.Textbox(visible=True, elem_classes=["hidden-el"], elem_id="fav_id_input")
            fav_index_input = gr.Textbox(visible=True, elem_classes=["hidden-el"], elem_id="fav_index_input")
            fav_trigger_btn = gr.Button(visible=True, elem_classes=["hidden-el"], elem_id="fav_trigger_btn")
            init_json_id = gr.Textbox(visible=True, elem_classes=["hidden-el"], elem_id="init_json_id")

    # 設定畫面 → 閱讀畫面
    to_read_btn.click(
        None, None, None,
        js="() => { document.querySelector('#main_tabs button[role=tab]:first-child').click(); }"
    )

    # 閱讀畫面 → 設定畫面
    to_setting_btn.click(
        None, None, None,
        js="() => { document.querySelector('#main_tabs button[role=tab]:nth-child(2)').click(); }"
    )

    # =========================
    # JSON / 匯入
    # =========================

    story_dropdown.change(
        lambda s, d: gr.update(choices=get_chapter_list(d, s)),
        inputs=[story_dropdown, story_data],
        outputs=chapter_dropdown
    )

    json_btn.click(
        load_drive_json,
        inputs=json_input,
        outputs=story_data
    ).then(
        lambda d: gr.update(choices=get_story_list(d)),
        inputs=story_data,
        outputs=story_dropdown
    ).then(
        None, inputs=json_input, outputs=None,
        js="""
        (jsonId) => {
            if (jsonId && jsonId.trim()) {
                localStorage.setItem("custom_json_id", jsonId.trim());
            }
        }
        """
    )

    app.load(
        lambda d: gr.update(choices=get_story_list(d)),
        inputs=story_data,
        outputs=story_dropdown
    )

    # ── 匯入內容按鈕：載入完畢後顯示綠色 Toast ─────────────────────────
    load_btn.click(
        download_drive_text,
        inputs=chapter_dropdown,
        outputs=html_display
    ).then(
        format_paragraphs,
        inputs=html_display,
        outputs=html_display
    ).then(
        update_title,
        inputs=[story_dropdown, chapter_dropdown, story_data],
        outputs=title_display
    ).then(
        None, None, None,
        js=f"""
        () => {{
            // 匯入新內容時，完全重置播放狀態
            speechSynthesis.cancel();
            window.player = null;
            let savedFontSize = localStorage.getItem("font_size");
            if (savedFontSize) {{
                document.querySelectorAll(".paragraph").forEach(p => {{
                    p.style.fontSize = savedFontSize + "px";
                }});
            }}

            // ✅ 顯示匯入完畢提示（綠色）
            {TOAST_JS_GREEN}

            // 自動跳至閱讀畫面
            document.querySelector('#main_tabs button[role=tab]:first-child').click();
        }}
        """
    )

    # ── 我的最愛按鈕：載入完畢後顯示橘色 Toast ─────────────────────────
    fav_trigger_btn.click(
        download_drive_text,
        inputs=fav_id_input,
        outputs=html_display
    ).then(
        format_paragraphs,
        inputs=html_display,
        outputs=html_display
    ).then(
        None, None, None,
        js=f"""
        () => {{
            speechSynthesis.cancel();
            window.player = null;

            let savedFontSize = localStorage.getItem("font_size");
            if (savedFontSize) {{
                document.querySelectorAll(".paragraph").forEach(p => {{
                    p.style.fontSize = savedFontSize + "px";
                }});
            }}

            // ⭐ 顯示最愛載入提示（橘色）
            {TOAST_JS_ORANGE}

            // 自動跳至閱讀畫面
            document.querySelector('#main_tabs button[role=tab]:first-child').click();
        }}
        """
    )

    # =========================
    # 事件邏輯
    # =========================

    story_dropdown.change(
        lambda s, d: gr.update(choices=get_chapter_list(d, s)),
        [story_dropdown, story_data],
        chapter_dropdown
    )

    font_size.change(
        None,
        inputs=font_size,
        outputs=None,
        js="""
        (size) => {
            document.querySelectorAll(".paragraph").forEach(p => {
                p.style.fontSize = size + "px";
            });
            localStorage.setItem("font_size", size);
        }
        """
    )

    init_json_id.change(
        load_drive_json,
        inputs=init_json_id,
        outputs=story_data
    ).then(
        lambda d: gr.update(choices=get_story_list(d)),
        inputs=story_data,
        outputs=story_dropdown
    ).then(
        None, None, None,
        js="""
        () => {
            speechSynthesis.cancel();
            window.player = null;
            // 自動跳至閱讀畫面
            document.querySelector('#main_tabs button[role=tab]:first-child').click();
        }
        """
    )

    # 播放 JS 邏輯
    play_js = """
    (html, rate, pitch, selectedVoice, storyKey, chapterKey) => {
        if (!html) return;
        // 暫停中則續播
        if (window.player && window.player.isPaused && window.player.html === html) {
            window.player.isPaused = false;
            // 先嘗試 resume，若無效則重新 speak
            speechSynthesis.resume();
            setTimeout(() => {
                if (!speechSynthesis.speaking) {
                    // 螢幕恢復後 resume 無效，重新從當前段落播放
                    speechSynthesis.cancel();
                    window.speakFrom(window.player.index);
                }
            }, 500);
            return;
        }
        speechSynthesis.cancel();

        let nodes = document.querySelectorAll(".paragraph");
        let paragraphs = Array.from(nodes).map(p => p.innerText);

        window.player = {
            html: html,
            id: chapterKey || "fav_play",
            paragraphs: paragraphs,
            nodes: nodes,
            index: 0,
            isPaused: false,
            rate: rate,
            pitch: pitch,
        };
        if (window._fav_pending) {
            window.player.index = window._fav_pending.index;
            window._fav_pending = null;
        }

        function speakNext() {
            if (window.player.isPaused || window.player.index >= window.player.paragraphs.length) return;

            // 視覺高亮
            window.player.nodes.forEach(n => n.classList.remove("highlight"));
            let currentNode = window.player.nodes[window.player.index];
            if(currentNode) {
                currentNode.classList.add("highlight");
                currentNode.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            let utter = new SpeechSynthesisUtterance(window.player.paragraphs[window.player.index]);
            utter.rate = window.player.rate;
            utter.pitch = window.player.pitch;
            let currentVoiceName = document.querySelector("#voice_select")?.value;
            utter.voice = speechSynthesis.getVoices().find(v => v.name === currentVoiceName);

            utter.onend = () => {
                if (!window.player.isPaused) {
                    window.player.index++;
                    speakNext();
                }
            };
            speechSynthesis.speak(utter);
            document.getElementById("time_display") &&
                (document.getElementById("time_display").innerText = "正在播放第 " + (window.player.index + 1) + " 段");
        }
        speakNext();
    }
    """

    play_btn.click(
        None,
        [html_display, rate, pitch, voice_dropdown, story_dropdown, chapter_dropdown],
        None,
        js=play_js
    )

    pause_btn.click(None, None, None, js="""
    () => {
        if (!window.player) return;
        window.player.isPaused = true;
        speechSynthesis.pause();

        // 存入 LocalStorage
        let favorites = JSON.parse(localStorage.getItem("story_favs") || "{}");
        let storyTitle = document.querySelector('[aria-label="選擇書籍"]')?.value || "未命名書籍";
        let chapterTitle = document.querySelector('[aria-label="選擇章節"]')?.value || "未命名章節";
        favorites[window.player.id] = {
            id: window.player.id,
            title: storyTitle + " - " + chapterTitle,
            index: window.player.index
        };
        localStorage.setItem("story_favs", JSON.stringify(favorites));

        // 自動刷新最愛清單
        let html = "";
        for (let k in favorites) {
            html += `
            <div style="display:flex; gap:4px; margin-bottom:4px;">
                <button class="fav-btn" data-key="${k}" style="flex:1; text-align:left; padding:8px; cursor:pointer; border:1px solid #ddd; border-radius:4px; background:#f9f9f9;">
                    ${favorites[k].title}
                </button>
                <button class="fav-del-btn" data-key="${k}" style="padding:8px 12px; cursor:pointer; border:1px solid #ffaaaa; border-radius:4px; background:#fff0f0; color:#cc0000;">
                    🗑
                </button>
            </div>`;
        }
        document.querySelector("#fav_list").innerHTML = html || "尚無收藏";
    }
    """)

    stop_btn.click(None, None, None, js="""() => {
        if (window.player && !window.player.isPaused) {
            if (!confirm("確定要停止播放？停止後將從頭開始朗讀。")) {
                return;
            }
        }
        if (window.player) {
            window.player.isPaused = true;
            window.player.index = 0;
            window.player = null;
        }
        speechSynthesis.cancel();
    }""")

    # 全域事件委派：處理最愛按鈕點擊
    app.load(None, None, None, js="""
    () => {
        // 讀取已儲存的字體大小
        let savedFontSize = localStorage.getItem("font_size");
        if (savedFontSize) {
            document.querySelectorAll(".paragraph").forEach(p => {
                p.style.fontSize = savedFontSize + "px";
            });
        }

        // 1. 讀取並顯示最愛清單
        window.renderFavList = function() {
            let fav = JSON.parse(localStorage.getItem("story_favs") || "{}");
            let html = "";
            for (let k in fav) {
                html += `
                <div style="display:flex; gap:4px; margin-bottom:4px;">
                    <button class="fav-btn" data-key="${k}" style="flex:1; text-align:left; padding:8px; cursor:pointer; border:1px solid #ddd; border-radius:4px; background:#f9f9f9;">
                        ${fav[k].title}
                    </button>
                    <button class="fav-del-btn" data-key="${k}" style="padding:8px 12px; cursor:pointer; border:1px solid #ffaaaa; border-radius:4px; background:#fff0f0; color:#cc0000;">
                        🗑
                    </button>
                </div>`;
            }
            let favList = document.querySelector("#fav_list");
            if (favList) favList.innerHTML = html || "尚無收藏";
        }

        // 2. 讀取 localStorage 的 json id，若無則用預設
        function waitAndInit() {
            let favList = document.querySelector("#fav_list");
            let initEl = document.querySelector("#init_json_id textarea");

            if (!favList || !initEl) {
                setTimeout(waitAndInit, 50);
                return;
            }

            // 元素已就緒，執行初始化
            window.renderFavList();

            let savedId = localStorage.getItem("custom_json_id") || "1WrNyH65rrX9NN_hr20xL6uDZpydycA46";
            initEl.value = savedId;
            initEl.dispatchEvent(new Event("input", { bubbles: true }));

            let savedFontSize = localStorage.getItem("font_size");
            if (savedFontSize) {
                document.querySelectorAll(".paragraph").forEach(p => {
                    p.style.fontSize = savedFontSize + "px";
                });
            }

            // 動態計算文字方塊高度
            function adjustNovelBox() {
                let box = document.querySelector("#novel_content");
                if (!box) return;
                let windowH = window.innerHeight;
                let boxTop = box.getBoundingClientRect().top;
                let newH = windowH - boxTop - 20;
                box.style.height = Math.max(200, newH) + "px";
            }
            adjustNovelBox();
            window.addEventListener("resize", adjustNovelBox);
        }

        waitAndInit();

        // 3. 載入語音清單
        function loadVoices() {
            let voices = speechSynthesis.getVoices();
            if (voices.length === 0) return;
            let filtered = voices.filter(v =>
                v.lang.startsWith("zh") ||
                v.lang.startsWith("cmn") ||
                v.lang.startsWith("yue")
            );
            if (filtered.length === 0) filtered = voices;

            let container = document.querySelector("#voice_selector_container");
            if (!container) return;

            let html = `<label style="font-size:14px; color:#666;">音色</label>
            <select id="voice_select" onchange="
                let val = this.value;
                let el = document.querySelector('#voice_value textarea');
                if (el) { el.value = val; el.dispatchEvent(new Event('input', {bubbles:true})); }
            ">`;
            filtered.forEach(v => {
                html += `<option value="${v.name}">${v.name} (${v.lang})</option>`;
            });
            html += `</select>`;
            container.innerHTML = html;

            let el = document.querySelector("#voice_value textarea");
            if (el && filtered[0]) {
                el.value = filtered[0].name;
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }
        }
        speechSynthesis.onvoiceschanged = loadVoices;
        setTimeout(loadVoices, 500);

        // 4. 最愛點擊與刪除事件
        document.addEventListener("click", (e) => {
            if (e.target.classList.contains("fav-btn")) {
                let key = e.target.getAttribute("data-key");
                let fav = JSON.parse(localStorage.getItem("story_favs") || "{}");
                let data = fav[key];
                if (!data) return;

                window._fav_pending = { id: data.id, index: data.index || 0 };

                let el = document.querySelector("#fav_id_input textarea");
                if (!el) {
                    console.error("找不到 #fav_id_input textarea");
                    return;
                }
                el.value = data.id;
                el.dispatchEvent(new Event("input", { bubbles: true }));

                setTimeout(() => {
                    let btn = document.querySelector("#fav_trigger_btn");
                    if (btn) btn.click();
                    else console.error("找不到 #fav_trigger_btn");
                }, 100);
            }
            if (e.target.classList.contains("fav-del-btn")) {
                let key = e.target.getAttribute("data-key");
                let fav = JSON.parse(localStorage.getItem("story_favs") || "{}");
                delete fav[key];
                localStorage.setItem("story_favs", JSON.stringify(fav));

                let html = "";
                for (let k in fav) {
                    html += `
                    <div style="display:flex; gap:4px; margin-bottom:4px;">
                        <button class="fav-btn" data-key="${k}" style="flex:1; text-align:left; padding:8px; cursor:pointer; border:1px solid #ddd; border-radius:4px; background:#f9f9f9;">
                            ${fav[k].title}
                        </button>
                        <button class="fav-del-btn" data-key="${k}" style="padding:8px 12px; cursor:pointer; border:1px solid #ffaaaa; border-radius:4px; background:#fff0f0; color:#cc0000;">
                            🗑
                        </button>
                    </div>`;
                }
                document.querySelector("#fav_list").innerHTML = html || "尚無收藏";
            }
        });
        // 偵測螢幕重新開啟
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                // speechSynthesis 狀態重置
                speechSynthesis.cancel();
                
                if (window.player) {
                    // 強制標記為暫停，等使用者手動按播放
                    window.player.isPaused = true;
                    
                    // 更新 html 比對值，避免誤判為不同文章
                    let nodes = document.querySelectorAll(".paragraph");
                    window.player.nodes = nodes;
                }
            }
        });
    }
    """)

app.launch()