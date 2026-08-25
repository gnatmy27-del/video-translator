"""
视频翻译工具 - 主程序
带图形界面，选择视频后自动识别语音（多语言）并生成字幕（可翻译成多种语言）
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 将当前目录加入路径，确保模块可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _app_dir() -> str:
    """应用数据目录：源码模式=项目目录；exe 打包后=exe 所在目录"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


from transcriber import JapaneseTranscriber
from translator import Translator, SOURCE_LANGUAGES, TARGET_LANGUAGES
from subtitle_gen import generate_srt


class VideoTranslatorApp:
    """主应用窗口"""

    # 模型选项：(显示名, 模型ID, 大致显存/内存需求)
    MODEL_OPTIONS = [
        ("tiny   (最快，约75MB，准确率较低)", "tiny"),
        ("base   (较快，约145MB)", "base"),
        ("small  (推荐，约460MB，多语言通用)", "small"),
        ("medium (较准，约1.5GB，较慢)", "medium"),
        ("large-v3 (最准，约3GB，最慢)", "large-v3"),
    ]

    DEVICE_OPTIONS = ["自动", "CPU", "CUDA (NVIDIA显卡)"]

    # 外观主题配色（bg 背景 / fg 文字 / panel 面板 / entry 输入框 / accent 强调色 / hint 提示灰字）
    THEMES = {
        "亮色": {
            "bg": "#f2f4f8", "fg": "#1f2329",
            "panel": "#ffffff", "panel_fg": "#1f2329",
            "entry_bg": "#ffffff", "entry_fg": "#1f2329",
            "accent": "#2563eb", "accent_fg": "#ffffff",
            "hint": "#6b7280",
            "log_bg": "#f7f8fb", "log_fg": "#1f2329",
        },
        "暗色": {
            "bg": "#1e1f24", "fg": "#e4e4e9",
            "panel": "#2a2b32", "panel_fg": "#e4e4e9",
            "entry_bg": "#3a3b44", "entry_fg": "#f0f0f4",
            "accent": "#3b82f6", "accent_fg": "#ffffff",
            "hint": "#9ca3af",
            "log_bg": "#141418", "log_fg": "#c9c9d2",
        },
        "森系绿": {
            "bg": "#eef4ea", "fg": "#23301f",
            "panel": "#fbfdf9", "panel_fg": "#23301f",
            "entry_bg": "#ffffff", "entry_fg": "#1f291d",
            "accent": "#2f855a", "accent_fg": "#ffffff",
            "hint": "#5f6e58",
            "log_bg": "#e6efe0", "log_fg": "#23301f",
        },
        "海洋蓝": {
            "bg": "#e9f1fa", "fg": "#1b2a3a",
            "panel": "#fcfdff", "panel_fg": "#1b2a3a",
            "entry_bg": "#ffffff", "entry_fg": "#16222f",
            "accent": "#0369a1", "accent_fg": "#ffffff",
            "hint": "#51677d",
            "log_bg": "#e0ecf9", "log_fg": "#1b2a3a",
        },
        "暗夜紫": {
            "bg": "#181422", "fg": "#e6e0f0",
            "panel": "#221c31", "panel_fg": "#e6e0f0",
            "entry_bg": "#32294a", "entry_fg": "#f2eefb",
            "accent": "#a78bfa", "accent_fg": "#1a1526",
            "hint": "#9b8fb8",
            "log_bg": "#0f0c18", "log_fg": "#c8bfdd",
        },
        "樱花粉": {
            "bg": "#fdf0f3", "fg": "#3a232c",
            "panel": "#fffafa", "panel_fg": "#3a232c",
            "entry_bg": "#ffffff", "entry_fg": "#2e1a22",
            "accent": "#d94678", "accent_fg": "#ffffff",
            "hint": "#85606c",
            "log_bg": "#fbe9ef", "log_fg": "#3a232c",
        },
        "暖阳橙": {
            "bg": "#fbf3e9", "fg": "#332518",
            "panel": "#fffaf2", "panel_fg": "#332518",
            "entry_bg": "#ffffff", "entry_fg": "#2a1f13",
            "accent": "#ea580c", "accent_fg": "#ffffff",
            "hint": "#8a6f52",
            "log_bg": "#f7e9d8", "log_fg": "#332518",
        },
    }
    # 主题下拉框的选项顺序（"跟随系统"在最前）
    THEME_OPTIONS = ["跟随系统", "亮色", "暗色", "森系绿", "海洋蓝", "暗夜紫", "樱花粉", "暖阳橙"]

    def __init__(self, root):
        self.root = root
        self.root.title("视频翻译工具 - Video Translator")
        self.root.geometry("720x680")
        self.root.minsize(640, 560)

        # 状态变量
        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=os.path.expanduser("~"))
        self.model_var = tk.StringVar(value=self.MODEL_OPTIONS[2][0])
        self.device_var = tk.StringVar(value="自动")
        self.translate_var = tk.BooleanVar(value=True)
        self.bilingual_var = tk.BooleanVar(value=True)
        self.sing_var = tk.BooleanVar(value=False)  # 包含唱歌/音乐段落
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="就绪")

        # 语言选择（从 config.json 读取上次选择）
        _cfg = self._load_config()
        self.source_lang_var = tk.StringVar(
            value=_cfg.get("source_lang", "日语"))
        self.target_lang_var = tk.StringVar(
            value=_cfg.get("target_lang", "中文(简体)"))

        # 外观主题（从 config.json 读取上次选择，默认跟随系统）
        self.theme_var = tk.StringVar(
            value=_cfg.get("theme", "跟随系统"))

        # DeepSeek API Key（可选，从 config.json 读取）
        self.api_key_var = tk.StringVar(
            value=self._load_config().get("deepseek_api_key", ""))

        # 视频背景描述（可选，帮助翻译理解剧情，从 config.json 读取）
        self._saved_context = self._load_config().get("video_context", "")

        # 分类2：选择已有字幕文件
        self.srt_file_var = tk.StringVar()

        # 运行控制
        self._worker_thread = None
        self._stop_flag = False
        self.last_srt_path = None  # 最近生成的字幕文件路径
        self._console_log_path = os.path.join(
            _app_dir(), "logs", "app.log")
        self.log_text = None  # 运行日志框（在设置页创建）
        self._float_windows = []  # 兼容旧引用
        self._floating_log = None  # 兼容旧引用
        # 日志文件读取偏移（只显示本次运行以来的新日志）
        self._log_offset = 0
        try:
            if os.path.exists(self._console_log_path):
                self._log_offset = os.path.getsize(self._console_log_path)
        except Exception:
            pass

        self._build_ui()
        self._poll_log_file()
    # ---------- 配置文件 ----------

    @staticmethod
    def _config_path() -> str:
        return os.path.join(_app_dir(), "config.json")

    @staticmethod
    def _load_config() -> dict:
        try:
            if os.path.exists(VideoTranslatorApp._config_path()):
                import json
                with open(VideoTranslatorApp._config_path(), encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_config(self):
        import json
        try:
            cfg = self._load_config()
            cfg["deepseek_api_key"] = self.api_key_var.get().strip()
            cfg["video_context"] = self.context_text.get("1.0", "end-1c").strip()
            cfg["source_lang"] = self.source_lang_var.get()
            cfg["target_lang"] = self.target_lang_var.get()
            cfg["theme"] = self.theme_var.get()
            with open(self._config_path(), "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- 外观主题 ----------

    @staticmethod
    def _detect_system_theme() -> str:
        """读取 Windows 系统主题（亮色/暗色），默认亮色"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "亮色" if val else "暗色"
        except Exception:
            return "亮色"

    def _current_palette(self) -> dict:
        """解析当前主题对应的配色（"跟随系统"时按系统主题切换）"""
        name = self.theme_var.get()
        if name == "跟随系统":
            name = self._detect_system_theme()
        return self.THEMES.get(name, self.THEMES["亮色"])

    def _apply_theme(self):
        """按当前选择的主题重新设置界面配色"""
        T = self._current_palette()

        style = ttk.Style()
        try:
            # clam 主题完整支持自定义配色（vista 会忽略页签等控件的颜色）
            style.theme_use("clam")
        except Exception:
            pass

        # 基础控件
        style.configure("TFrame", background=T["bg"])
        style.configure("TLabel", background=T["bg"], foreground=T["fg"])
        style.configure("Hint.TLabel", background=T["bg"], foreground=T["hint"])
        style.configure("TLabelFrame", background=T["bg"], foreground=T["panel_fg"])
        style.configure("TLabelFrame.Label", background=T["bg"], foreground=T["fg"])

        # 按钮
        style.configure("TButton", background=T["panel"], foreground=T["fg"],
                        padding=(12, 5), font=("Microsoft YaHei UI", 9),
                        borderwidth=1, relief="flat")
        style.map("TButton",
                  background=[("active", T["entry_bg"]), ("pressed", T["entry_bg"])],
                  foreground=[("active", T["fg"]), ("pressed", T["fg"])])
        style.configure("Accent.TButton", background=T["accent"], foreground=T["accent_fg"],
                        padding=(12, 5), font=("Microsoft YaHei UI", 9),
                        borderwidth=0, relief="flat")
        style.map("Accent.TButton",
                  background=[("active", T["accent"]), ("pressed", T["accent"])],
                  foreground=[("active", T["accent_fg"]), ("pressed", T["accent_fg"])])

        # 输入框 / 下拉框
        style.configure("TEntry", fieldbackground=T["entry_bg"], foreground=T["entry_fg"],
                        insertcolor=T["fg"])
        style.map("TEntry", fieldbackground=[("readonly", T["entry_bg"])])
        style.configure("TCombobox", fieldbackground=T["entry_bg"], foreground=T["entry_fg"],
                        background=T["entry_bg"], arrowcolor=T["fg"], bordercolor=T["panel"])
        style.map("TCombobox",
                  fieldbackground=[("readonly", T["entry_bg"])],
                  foreground=[("readonly", T["entry_fg"])])

        # 复选框
        style.configure("TCheckbutton", background=T["bg"], foreground=T["fg"])
        style.map("TCheckbutton",
                  background=[("active", T["bg"])],
                  foreground=[("active", T["fg"])])

        # 页签：选中态用强调色高亮并微微凸起，未选中用面板色，清晰可辨
        style.configure("TNotebook", background=T["bg"], borderwidth=0,
                        tabmargins=[6, 4, 6, 0])
        style.configure("TNotebook.Tab", background=T["panel"], foreground=T["panel_fg"],
                        padding=(16, 7), font=("Microsoft YaHei UI", 10), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", T["accent"]), ("active", T["panel"])],
                  foreground=[("selected", T["accent_fg"]), ("active", T["panel_fg"])],
                  expand=[("selected", (1, 1, 1, 0))])

        # 进度条
        style.configure("TProgressbar", troughcolor=T["panel"], background=T["accent"],
                        borderwidth=0)

        # 主窗口和直接创建的 tk 控件
        self.root.configure(bg=T["bg"])
        try:
            if getattr(self, "mdic", None) is not None:
                self.mdic.configure(bg=T["bg"])
            if self.log_text is not None:
                self.log_text.configure(bg=T["log_bg"], fg=T["log_fg"],
                                        insertbackground=T["log_fg"])
            self.context_text.configure(bg=T["entry_bg"], fg=T["entry_fg"],
                                        insertbackground=T["fg"])
            self.status_label.configure(foreground=T["fg"], background=T["bg"])
        except Exception:
            pass

    def _theme_changed(self, *_):
        """主题切换时立即应用并保存"""
        self._apply_theme()
        try:
            self._save_config()
        except Exception:
            pass

    def _build_ui(self):
        """构建界面（标准版：三个页签，不支持多窗口分屏）"""
        # ===== 顶部分类页签 =====
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # ===== 页签①：视频翻译字幕 =====
        main = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(main, text="① 视频翻译字幕")
        self._build_translate_content(main)

        # ===== 页签②：修改已有字幕 =====
        tab_edit = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab_edit, text="② 修改已有字幕")
        self._build_edit_content(tab_edit)

        # ===== 页签③：设置 =====
        tab_settings = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(tab_settings, text="③ 设置")
        self._build_settings_content(tab_settings)

        # 应用主题
        self._apply_theme()

    def _build_translate_content(self, main):
        """构建页签①内容（视频翻译字幕）"""

        # ===== 第一步：选择视频 =====
        step1 = ttk.LabelFrame(main, text=" ① 选择视频文件 ", padding=10)
        step1.pack(fill=tk.X, pady=(0, 8))

        path_row = ttk.Frame(step1)
        path_row.pack(fill=tk.X)
        ttk.Entry(path_row, textvariable=self.video_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
        )
        ttk.Button(path_row, text="浏览...", command=self._browse_video).pack(side=tk.LEFT)

        ttk.Label(step1, text="支持 MP4 / MKV / AVI / MOV / FLV / WebM 等常见格式",
                  style="Hint.TLabel").pack(anchor=tk.W, pady=(6, 0))

        # ===== 第二步：识别设置 =====
        step2 = ttk.LabelFrame(main, text=" ② 语音识别设置 ", padding=10)
        step2.pack(fill=tk.X, pady=(0, 8))

        grid = ttk.Frame(step2)
        grid.pack(fill=tk.X)

        ttk.Label(grid, text="模型大小：").grid(row=0, column=0, sticky=tk.W, pady=3)
        model_combo = ttk.Combobox(
            grid, textvariable=self.model_var,
            values=[m[0] for m in self.MODEL_OPTIONS],
            state="readonly", width=42
        )
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=(6, 0), pady=3)

        ttk.Label(grid, text="计算设备：").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(
            grid, textvariable=self.device_var,
            values=self.DEVICE_OPTIONS, state="readonly", width=20
        ).grid(row=1, column=1, sticky=tk.W, padx=(6, 0), pady=3)

        ttk.Label(grid, text="识别语言：").grid(row=2, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(
            grid, textvariable=self.source_lang_var,
            values=list(SOURCE_LANGUAGES.keys()),
            state="readonly", width=20
        ).grid(row=2, column=1, sticky=tk.W, padx=(6, 0), pady=3)

        ttk.Checkbutton(
            step2, text="☑ 包含唱歌/音乐段落（舞台剧、演唱会用，关闭人声过滤、识别更全但稍慢）",
            variable=self.sing_var
        ).pack(anchor=tk.W, pady=(6, 0))

        # ===== 第三步：翻译与输出 =====
        step3 = ttk.LabelFrame(main, text=" ③ 翻译与输出设置 ", padding=10)
        step3.pack(fill=tk.X, pady=(0, 8))

        ttk.Checkbutton(
            step3, text="翻译字幕（关闭则只生成原文字幕）",
            variable=self.translate_var
        ).pack(anchor=tk.W)

        ttk.Checkbutton(
            step3, text="双语字幕（原文 + 译文同时显示）",
            variable=self.bilingual_var
        ).pack(anchor=tk.W, pady=(4, 0))

        lang_row = ttk.Frame(step3)
        lang_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(lang_row, text="翻译为：").pack(side=tk.LEFT)
        ttk.Combobox(
            lang_row, textvariable=self.target_lang_var,
            values=list(TARGET_LANGUAGES.keys()),
            state="readonly", width=16
        ).pack(side=tk.LEFT, padx=(6, 0))

        # DeepSeek API Key 输入（可选）
        key_row = ttk.Frame(step3)
        key_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(key_row, text="DeepSeek API Key(可选):").pack(side=tk.LEFT)
        ttk.Entry(key_row, textvariable=self.api_key_var, show="*").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6)
        )
        ttk.Button(key_row, text="保存", command=self._save_config).pack(side=tk.LEFT)
        ttk.Label(
            step3,
            text="填了用它翻译（质量高、容错强），留空用免费翻译（MyMemory）",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        # 视频背景描述（可选，帮助 AI 翻译理解剧情）
        ttk.Label(step3, text="视频背景描述(可选,帮助翻译更准确)：").pack(anchor=tk.W, pady=(8, 0))
        self.context_text = tk.Text(step3, height=3, wrap=tk.WORD)
        self.context_text.pack(fill=tk.X, pady=(4, 0))
        if self._saved_context:
            self.context_text.insert("1.0", self._saved_context)
        ttk.Label(
            step3,
            text="例：这是XX舞台剧第X幕，主角是奥斯卡，故事发生在18世纪的法国……",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        out_row = ttk.Frame(step3)
        out_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(out_row, text="输出目录：").pack(side=tk.LEFT)
        ttk.Entry(out_row, textvariable=self.output_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6)
        )
        ttk.Button(out_row, text="更改", command=self._browse_output_dir).pack(side=tk.LEFT)

        # ===== 操作按钮 =====
        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=(4, 8))

        self.start_btn = ttk.Button(btn_row, text="▶  开始翻译", command=self._start,
                                    style="Accent.TButton")
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = ttk.Button(
            btn_row, text="■  停止", command=self._stop, state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.edit_btn = ttk.Button(
            btn_row, text="✏️  打开字幕编辑器", command=self._open_subtitle_editor,
            state=tk.DISABLED
        )
        self.edit_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 进度条
        ttk.Progressbar(main, variable=self.progress_var, maximum=100).pack(fill=tk.X)
        self.status_label = tk.Label(main, textvariable=self.status_var,
                                     anchor=tk.W, font=("Microsoft YaHei UI", 9))
        self.status_label.pack(fill=tk.X, pady=(4, 0))

    def _build_edit_content(self, tab_edit):
        """构建页签②内容（修改已有字幕）"""
        ttk.Label(
            tab_edit,
            text="选择一个已经生成好的 .srt 字幕文件，直接修改其中的翻译或日文原文。\n"
                 "不需要先跑翻译流程，随时可以用。",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor=tk.W)

        # 文件选择
        file_row = ttk.Frame(tab_edit)
        file_row.pack(fill=tk.X, pady=(16, 0))
        ttk.Label(file_row, text="字幕文件：").pack(side=tk.LEFT)
        ttk.Entry(file_row, textvariable=self.srt_file_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6)
        )
        ttk.Button(file_row, text="浏览...", command=self._browse_srt).pack(side=tk.LEFT)

        # 打开按钮
        open_row = ttk.Frame(tab_edit)
        open_row.pack(fill=tk.X, pady=(16, 0))
        ttk.Button(
            open_row, text="✏️  打开字幕编辑器", command=self._open_srt_editor
        ).pack(side=tk.LEFT)

        # 最近生成的字幕（动态更新）
        self.recent_srt_var = tk.StringVar(value="")
        recent_row = ttk.Frame(tab_edit)
        recent_row.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(
            recent_row, text="打开最近生成的字幕", command=self._open_recent_srt
        ).pack(side=tk.LEFT)
        ttk.Label(recent_row, textvariable=self.recent_srt_var,
                  style="Hint.TLabel", wraplength=560).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        ttk.Label(
            tab_edit,
            text="提示：编辑器支持「查找」定位错句、直接改文字、Ctrl+Z 撤销、删除整条字幕；\n"
                 "修改后点「保存」，再用播放器重新加载字幕即可生效。",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(20, 0))

    def _build_settings_content(self, tab_settings):
        """构建页签③内容（设置）"""
        # 外观主题
        ttk.Label(tab_settings, text="外观主题", font=("Microsoft YaHei UI", 10, "bold")
                  ).pack(anchor=tk.W)
        theme_row = ttk.Frame(tab_settings)
        theme_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(theme_row, text="界面主题：").pack(side=tk.LEFT)
        theme_combo = ttk.Combobox(
            theme_row, textvariable=self.theme_var,
            values=self.THEME_OPTIONS, state="readonly", width=14
        )
        theme_combo.pack(side=tk.LEFT, padx=(6, 0))
        theme_combo.bind("<<ComboboxSelected>>", self._theme_changed)
        ttk.Label(tab_settings,
                  text="「跟随系统」会自动匹配 Windows 的亮/暗模式；\n"
                       "另有 亮色 / 暗色 / 森系绿 / 海洋蓝 / 暗夜紫 / 樱花粉 / 暖阳橙 可自由切换。",
                  style="Hint.TLabel").pack(anchor=tk.W, pady=(4, 0))

        # 窗口说明
        ttk.Label(tab_settings, text="运行日志", font=("Microsoft YaHei UI", 10, "bold")
                  ).pack(anchor=tk.W, pady=(18, 0))
        ttk.Label(
            tab_settings,
            text="运行日志实时显示在此处（标准版内嵌显示，不弹额外窗口）。",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        # 运行日志（内嵌显示）
        log_frame = ttk.LabelFrame(tab_settings, text=" 运行日志（实时） ", padding=6)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.log_text = tk.Text(log_frame, height=12, wrap=tk.WORD,
                                font=("Consolas", 9))
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL,
                                   command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 关于
        ttk.Label(tab_settings, text="关于", font=("Microsoft YaHei UI", 10, "bold")
                  ).pack(anchor=tk.W, pady=(18, 0))
        ttk.Label(
            tab_settings,
            text="视频翻译工具（多语言 · 标准版）\n"
                 "语音识别：Whisper / faster-whisper（开源）\n"
                 "翻译：DeepSeek AI / MyMemory / Google\n"
                 "纯本地运行，视频不上传。",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(8, 0))

    # ---------- 悬浮窗口（MDI） ----------

    def _on_resize(self, event=None):
        """主窗口尺寸变化：同步页签尺寸，并把悬浮窗约束在窗口内"""
        if event is not None and event.widget is not self.root:
            return
        try:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            if w <= 1 or h <= 1:
                return
            self.mdic.configure(width=w, height=h)
            for fw in self._float_windows:
                if fw._closed:
                    continue
                try:
                    if fw._maximized:
                        fw._apply_maximize_size()
                        continue
                    coords = self.mdic.coords(fw.win_id)
                    if coords:
                        nx = max(0, min(coords[0], w - 30))
                        ny = max(0, min(coords[1], h - 24))
                        self.mdic.coords(fw.win_id, nx, ny)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_fw_close(self, fw):
        """悬浮窗关闭时清理引用"""
        if fw is self._floating_log:
            self._floating_log = None
        elif fw is self._floating_editor:
            self._floating_editor = None
        elif fw is self._floating_about:
            self._floating_about = None
        elif fw is self._module_translate:
            self._module_translate = None
        elif fw is self._module_edit:
            self._module_edit = None
        elif fw is self._module_settings:
            self._module_settings = None
        if fw in self._float_windows:
            self._float_windows.remove(fw)

    def _open_floating_log(self):
        """打开（或恢复）运行日志悬浮窗"""
        if self._floating_log and not self._floating_log._closed:
            self._floating_log.show()
            return
        fw = FloatingWindow(self.mdic, "运行日志", width=540, height=300,
                            icon="📋",
                            on_close=self._on_fw_close,
                            on_raise=lambda w: w.clear_badge())
        self.log_text = tk.Text(fw.content, wrap=tk.WORD,
                                font=("Consolas", 9))
        log_scroll = ttk.Scrollbar(fw.content, orient=tk.VERTICAL,
                                   command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 打开时显示最近的日志（尾部 200 行），并继续实时追加
        try:
            if os.path.exists(self._console_log_path):
                with open(self._console_log_path, "r", encoding="utf-8",
                          errors="replace") as f:
                    lines = f.readlines()
                tail = "".join(lines[-200:])
                if tail:
                    self.log_text.insert("1.0", tail)
                    self.log_text.see(tk.END)
                self._log_offset = os.path.getsize(self._console_log_path)
        except Exception:
            pass

        self._floating_log = fw
        self._float_windows.append(fw)

    def _open_floating_about(self):
        """打开（或恢复）关于悬浮窗"""
        if self._floating_about and not self._floating_about._closed:
            self._floating_about.show()
            return
        fw = FloatingWindow(self.mdic, "关于", width=380, height=220,
                            icon="ℹ️", on_close=self._on_fw_close)
        about = (
            "视频翻译工具（多语言）\n\n"
            "语音识别：Whisper / faster-whisper（开源）\n"
            "翻译：DeepSeek AI / MyMemory / Google\n"
            "字幕编辑：内置查找 / 替换 / 定位\n\n"
            "纯本地运行，视频不上传，隐私安全。"
        )
        tk.Label(fw.content, text=about, justify=tk.LEFT,
                 font=("Microsoft YaHei UI", 10),
                 bg="#f7f8fb", fg="#1f2329").pack(padx=16, pady=14, anchor=tk.NW)
        self._floating_about = fw
        self._float_windows.append(fw)

    def _open_floating_editor(self):
        """打开字幕编辑器悬浮窗（对应②页里的编辑功能）"""
        self._open_subtitle_editor()

    # ---------- 文件选择 ----------

    def _browse_video(self):
        path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.webm *.m4v *.ts"),
                ("所有文件", "*.*"),
            ]
        )
        if path:
            self.video_path.set(path)
            # 自动设置输出目录为视频所在目录
            self.output_dir.set(os.path.dirname(path))

    def _browse_output_dir(self):
        d = filedialog.askdirectory(title="选择输出目录", initialdir=self.output_dir.get())
        if d:
            self.output_dir.set(d)

    # ---------- 日志 ----------

    def _log(self, msg: str):
        """写日志到日志文件（设置页的「运行日志」框实时显示）"""
        try:
            os.makedirs(os.path.dirname(self._console_log_path), exist_ok=True)
            with open(self._console_log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    def _poll_log_file(self):
        """定期读取日志文件的新内容：写入日志框，并累计未读角标"""
        try:
            if os.path.exists(self._console_log_path):
                with open(self._console_log_path, "r", encoding="utf-8",
                          errors="replace") as f:
                    f.seek(self._log_offset)
                    new_text = f.read()
                    self._log_offset = f.tell()
                if new_text:
                    # 写入日志悬浮窗
                    if self.log_text is not None:
                        try:
                            self.log_text.insert(tk.END, new_text)
                            self.log_text.see(tk.END)
                            if float(self.log_text.index("end-1c")) > 3000:
                                self.log_text.delete("1.0", "2000.0")
                        except Exception:
                            pass
                    # 未读角标（VSCode 风格计数）
                    if self._floating_log and not self._floating_log._closed:
                        try:
                            self._floating_log._pending += new_text.count("\n")
                            self._floating_log.set_badge(
                                str(self._floating_log._pending))
                        except Exception:
                            pass
        except Exception:
            pass
        try:
            self.root.after(400, self._poll_log_file)
        except Exception:
            pass

    # ---------- 开始/停止 ----------

    def _start(self):
        video = self.video_path.get().strip()
        if not video:
            messagebox.showwarning("提示", "请先选择视频文件")
            return
        if not os.path.isfile(video):
            messagebox.showerror("错误", f"文件不存在：\n{video}")
            return

        self._stop_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.edit_btn.config(state=tk.DISABLED)  # 运行中先禁用编辑
        self.progress_var.set(0)
        if self.log_text is not None:
            self.log_text.delete("1.0", tk.END)
        self._save_config()  # 自动保存 API Key 和背景描述

        self._worker_thread = threading.Thread(target=self._run_pipeline, daemon=True)
        self._worker_thread.start()

    def _stop(self):
        self._stop_flag = True
        self.status_var.set("正在停止...")
        self._log("用户请求停止，等待当前步骤结束...")

    def _finish(self, success: bool, message: str):
        """任务结束，恢复界面"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set(message)
        if success:
            self.progress_var.set(100)
            self._log(f"\n✅ 完成！{message}")
        else:
            self._log(f"\n❌ 失败：{message}")

    # ---------- 核心流程 ----------

    def _run_pipeline(self):
        """在后台线程中运行完整流程"""
        try:
            video = self.video_path.get().strip()
            out_dir = self.output_dir.get().strip() or os.path.dirname(video)
            base_name = os.path.splitext(os.path.basename(video))[0]

            # 解析模型
            model_display = self.model_var.get()
            model_id = next((m[1] for m in self.MODEL_OPTIONS if m[0] == model_display), "small")

            # 解析设备
            device_display = self.device_var.get()
            if device_display == "CPU":
                device = "cpu"
            elif "CUDA" in device_display:
                device = "cuda"
            else:
                device = "auto"

            # 解析语言
            src_name = self.source_lang_var.get()
            tgt_name = self.target_lang_var.get()
            src_lang = SOURCE_LANGUAGES.get(src_name, SOURCE_LANGUAGES["日语"])
            tgt_lang = TARGET_LANGUAGES.get(tgt_name, TARGET_LANGUAGES["中文(简体)"])

            self._log(f"视频文件：{video}")
            self._log(f"模型：{model_id} | 设备：{device}")
            if device == "auto":
                self._log("（自动 = 优先使用 GPU，GPU 不可用时会自动回退到 CPU）")
            self._log(f"识别语言：{src_name}")
            self._log(f"翻译为：{tgt_name}")
            self._log(f"翻译：{'开启' if self.translate_var.get() else '关闭'}")
            self._log(f"唱歌/音乐段落：{'包含（已关闭人声过滤）' if self.sing_var.get() else '不包含（仅说话）'}")
            self._log("-" * 50)

            # ===== 步骤1：语音识别 =====
            self.status_var.set("正在加载模型并识别语音...")
            self._log(f"\n[1/3] 正在进行{src_name}语音识别...")
            self._log(f"（首次使用 {model_id} 模型会自动下载，请耐心等待）")

            transcriber = JapaneseTranscriber(model_size=model_id, device=device)

            def transcribe_progress(current, total, msg=""):
                if self._stop_flag:
                    return
                if total and total > 0:
                    pct = min(current / total * 100, 99)
                    self.progress_var.set(pct)
                self.status_var.set(f"识别中... {msg}")

            segments = transcriber.transcribe(
                video, language=src_lang["whisper"],
                progress_callback=transcribe_progress,
                vad_filter=not self.sing_var.get()
            )

            if self._stop_flag:
                self._finish(False, "已停止")
                return

            self._log(f"识别完成，共 {len(segments)} 个语音片段（实际设备：{transcriber.device}）")

            if not segments:
                self._log("⚠ 未检测到语音，可能是纯音乐/无对白视频")
                self._finish(False, "未检测到语音")
                return

            # ===== 步骤2：翻译 =====
            if self.translate_var.get():
                self.status_var.set("正在翻译...")
                self._log(f"\n[2/3] 正在将{src_name}翻译为{tgt_name}...")

                context_text = self.context_text.get("1.0", "end-1c").strip()
                translator = Translator(
                    backend="auto",
                    api_key=self.api_key_var.get().strip(),
                    context=context_text,
                    source_lang=src_name,
                    target_lang=tgt_name,
                )
                if translator.has_deepseek:
                    self._log("翻译引擎：DeepSeek AI（高容错，可处理识别偏差）")
                else:
                    self._log("翻译引擎：免费在线翻译（MyMemory）")
                    self._log("提示：如想获得更好的翻译质量，可在「③ 翻译与输出设置」填入 DeepSeek API Key")
                if context_text:
                    self._log("已带上视频背景描述，将帮助 AI 更准确翻译")
                texts = [s["text"] for s in segments]

                def translate_progress(current, total, text=""):
                    if self._stop_flag:
                        return
                    pct = 50 + (current / total * 45) if total > 0 else 50
                    self.progress_var.set(min(pct, 95))
                    self.status_var.set(f"翻译中... {current}/{total}")

                translations = translator.translate_batch(
                    texts, progress_callback=translate_progress
                )

                for seg, trans in zip(segments, translations):
                    seg["translation"] = trans

                translated_count = sum(1 for t in translations if t)
                self._log(f"翻译完成，成功 {translated_count}/{len(segments)} 条")
            else:
                self._log(f"\n[2/3] 跳过翻译（仅生成{src_name}字幕）")

            if self._stop_flag:
                self._finish(False, "已停止")
                return

            # ===== 步骤3：生成字幕 =====
            self.status_var.set("正在生成字幕文件...")
            self._log("\n[3/3] 正在生成 SRT 字幕文件...")

            srt_path = os.path.join(out_dir, f"{base_name}.srt")
            bilingual = self.bilingual_var.get() and self.translate_var.get()
            generate_srt(segments, srt_path, bilingual=bilingual)

            self.last_srt_path = srt_path
            self.edit_btn.config(state=tk.NORMAL)  # 启用字幕编辑器
            self.recent_srt_var.set(srt_path)      # 分类2里显示"最近生成"

            self._log(f"字幕文件已保存：{srt_path}")
            self._log("完成后可点「✏️ 打开字幕编辑器」微调翻译")
            self._finish(True, f"字幕已生成：{srt_path}")

        except Exception as e:
            import traceback
            self._log(f"\n❌ 发生错误：{e}")
            self._log(traceback.format_exc())
            self._finish(False, f"出错：{e}")

    # ---------- 字幕编辑器 ----------

    def _open_subtitle_editor(self, srt_path=None):
        """打开内置字幕编辑器，支持查找/替换/定位/批量替换"""
        srt_path = srt_path or self.last_srt_path
        if not srt_path or not os.path.isfile(srt_path):
            messagebox.showwarning("提示", "请先选择要修改的字幕文件")
            return

        try:
            with open(srt_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
            return

        # 打开独立字幕编辑器窗口
        win = tk.Toplevel(self.root)
        win.title("字幕编辑器 - %s" % os.path.basename(srt_path))
        win.geometry("820x680")
        win.minsize(620, 480)

        status_var = tk.StringVar()
        entry_count = content.strip().count("\n\n") + 1 if content.strip() else 0
        status_var.set("共约 %d 条字幕" % entry_count)

        # ===== 工具栏：查找 / 替换 / 定位 =====
        toolbar = ttk.LabelFrame(win, text=" 查找 / 替换 / 定位 ", padding=6)
        toolbar.pack(fill=tk.X, padx=10, pady=(8, 4))

        # 查找行
        r1 = ttk.Frame(toolbar)
        r1.pack(fill=tk.X, pady=2)
        ttk.Label(r1, text="查找:").pack(side=tk.LEFT)
        find_entry = ttk.Entry(r1)
        find_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        ttk.Button(r1, text="下一个", width=6,
                   command=lambda: self._ed_find_next(text_widget, find_entry, status_var)
                   ).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(r1, text="上一个", width=6,
                   command=lambda: self._ed_find_prev(text_widget, find_entry, status_var)
                   ).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(r1, text="高亮全部", width=8,
                   command=lambda: self._ed_highlight_all(text_widget, find_entry, status_var)
                   ).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(r1, text="清除", width=5,
                   command=lambda: self._ed_clear_hl(text_widget)
                   ).pack(side=tk.LEFT, padx=(2, 0))

        # 替换行
        r2 = ttk.Frame(toolbar)
        r2.pack(fill=tk.X, pady=2)
        ttk.Label(r2, text="替换为:").pack(side=tk.LEFT)
        repl_entry = ttk.Entry(r2)
        repl_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        ttk.Button(r2, text="替换", width=6,
                   command=lambda: self._ed_replace(text_widget, find_entry, repl_entry, status_var)
                   ).pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(r2, text="全部替换", width=8,
                   command=lambda: self._ed_replace_all(text_widget, find_entry, repl_entry, status_var, win)
                   ).pack(side=tk.LEFT, padx=(2, 0))

        # 定位行
        r3 = ttk.Frame(toolbar)
        r3.pack(fill=tk.X, pady=2)
        ttk.Label(r3, text="定位到第:").pack(side=tk.LEFT)
        go_entry = ttk.Entry(r3, width=8)
        go_entry.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(r3, text="条字幕").pack(side=tk.LEFT, padx=(2, 0))
        ttk.Button(r3, text="定位", width=6,
                   command=lambda: self._ed_goto(text_widget, go_entry, status_var, win)
                   ).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(r3, textvariable=status_var, foreground="#444").pack(side=tk.RIGHT)

        # 快捷键：回车查找/替换/定位，F3 下一个
        find_entry.bind("<Return>",
                        lambda e: self._ed_find_next(text_widget, find_entry, status_var))
        repl_entry.bind("<Return>",
                        lambda e: self._ed_replace(text_widget, find_entry, repl_entry, status_var))
        go_entry.bind("<Return>",
                      lambda e: self._ed_goto(text_widget, go_entry, status_var, win))
        win.bind("<F3>",
                 lambda e: self._ed_find_next(text_widget, find_entry, status_var))

        # ===== 文本区 =====
        ed_frame = ttk.Frame(win)
        ed_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)
        T = self._current_palette()
        text_widget = tk.Text(ed_frame, wrap=tk.WORD, undo=True,
                              font=("Microsoft YaHei UI", 10),
                              bg=T["entry_bg"], fg=T["entry_fg"],
                              insertbackground=T["fg"])
        ed_scroll = ttk.Scrollbar(ed_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=ed_scroll.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ed_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.insert("1.0", content)

        # 底部按钮
        bottom = ttk.Frame(win)
        bottom.pack(fill=tk.X, padx=10, pady=(4, 10))
        ttk.Label(
            bottom,
            text="支持：查找上一个/下一个（F3）、高亮全部、替换、全部替换（批量）、定位到第N条字幕；\n"
                 "直接改文字即可，注意保持「序号+时间轴+空行」格式不变",
            style="Hint.TLabel",
        ).pack(side=tk.LEFT)

        def save():
            try:
                new_content = text_widget.get("1.0", "end-1c")
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                messagebox.showinfo("保存成功", "字幕已保存：\n" + srt_path, parent=win)
            except Exception as e:
                messagebox.showerror("保存失败", str(e), parent=win)

        ttk.Button(bottom, text="💾 保存", command=save).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(bottom, text="关闭", command=win.destroy).pack(side=tk.RIGHT)

    # ---------- 编辑器功能实现 ----------

    @staticmethod
    def _ed_find_all(text_widget, keyword: str) -> list:
        """返回文本中所有匹配位置 [(start, end), ...]"""
        positions = []
        start = "1.0"
        while True:
            pos = text_widget.search(keyword, start, stopindex=tk.END, nocase=True)
            if not pos:
                break
            end = text_widget.index(f"{pos}+{len(keyword)}c")
            positions.append((pos, end))
            start = end
            if len(positions) > 20000:  # 防止极端情况
                break
        return positions

    @staticmethod
    def _ed_select(text_widget, pos, end):
        """选中并高亮一段文本，光标移到其后"""
        text_widget.tag_remove("found", "1.0", tk.END)
        text_widget.tag_add("found", pos, end)
        text_widget.tag_config("found", background="yellow", foreground="black")
        # 设为真实选区，方便"替换"直接操作
        try:
            text_widget.tag_remove(tk.SEL, "1.0", tk.END)
            text_widget.tag_add(tk.SEL, pos, end)
        except tk.TclError:
            pass
        text_widget.mark_set(tk.INSERT, end)
        text_widget.see(pos)

    @staticmethod
    def _ed_clear_hl(text_widget):
        """清除所有高亮"""
        text_widget.tag_remove("found", "1.0", tk.END)

    def _ed_find_next(self, text_widget, find_entry, status_var):
        keyword = find_entry.get().strip()
        if not keyword:
            return
        start = text_widget.index(tk.INSERT)
        pos = text_widget.search(keyword, start, stopindex=tk.END, nocase=True)
        if not pos:  # 到底后从头开始
            pos = text_widget.search(keyword, "1.0", stopindex=tk.END, nocase=True)
        if pos:
            end = text_widget.index(f"{pos}+{len(keyword)}c")
            self._ed_select(text_widget, pos, end)
            n = len(self._ed_find_all(text_widget, keyword))
            status_var.set("匹配 %d 处" % n)
        else:
            status_var.set("未找到「%s」" % keyword)

    def _ed_find_prev(self, text_widget, find_entry, status_var):
        keyword = find_entry.get().strip()
        if not keyword:
            return
        positions = self._ed_find_all(text_widget, keyword)
        if not positions:
            status_var.set("未找到「%s」" % keyword)
            return
        insert = text_widget.index(tk.INSERT)
        prev = None
        for pos, end in positions:
            if pos < insert:
                prev = (pos, end)
            else:
                break
        if prev is None:  # 已到开头，回绕到最后一个
            prev = positions[-1]
        self._ed_select(text_widget, prev[0], prev[1])
        status_var.set("匹配 %d 处" % len(positions))

    def _ed_highlight_all(self, text_widget, find_entry, status_var):
        keyword = find_entry.get().strip()
        if not keyword:
            return
        positions = self._ed_find_all(text_widget, keyword)
        text_widget.tag_remove("found", "1.0", tk.END)
        for pos, end in positions:
            text_widget.tag_add("found", pos, end)
        text_widget.tag_config("found", background="yellow", foreground="black")
        status_var.set("高亮 %d 处匹配" % len(positions))

    def _ed_replace(self, text_widget, find_entry, repl_entry, status_var):
        """替换当前匹配；若无选中匹配则从光标处替换下一个"""
        keyword = find_entry.get().strip()
        repl = repl_entry.get()
        if not keyword:
            return

        # 1) 如果当前选中区域正好匹配关键字，替换它
        try:
            sel_start = text_widget.index(tk.SEL_FIRST)
            sel_end = text_widget.index(tk.SEL_LAST)
            selected = text_widget.get(sel_start, sel_end)
        except tk.TclError:
            selected = None

        if selected is not None and selected.lower() == keyword.lower():
            text_widget.delete(sel_start, sel_end)
            text_widget.insert(sel_start, repl)
            text_widget.tag_remove("found", "1.0", tk.END)
            start = text_widget.index(f"{sel_start}+{len(repl)}c")
        else:
            # 2) 否则从光标后找下一个匹配并直接替换
            start = text_widget.index(tk.INSERT)
            pos = text_widget.search(keyword, start, stopindex=tk.END, nocase=True)
            if not pos:
                pos = text_widget.search(keyword, "1.0", stopindex=tk.END, nocase=True)
            if not pos:
                status_var.set("未找到「%s」" % keyword)
                return
            text_widget.delete(pos, text_widget.index(f"{pos}+{len(keyword)}c"))
            text_widget.insert(pos, repl)
            text_widget.tag_remove("found", "1.0", tk.END)
            start = text_widget.index(f"{pos}+{len(repl)}c")

        # 定位到下一个匹配
        npos = text_widget.search(keyword, start, stopindex=tk.END, nocase=True)
        if npos:
            nend = text_widget.index(f"{npos}+{len(keyword)}c")
            self._ed_select(text_widget, npos, nend)
        n = len(self._ed_find_all(text_widget, keyword))
        status_var.set("已替换，剩余匹配 %d 处" % n)

    def _ed_replace_all(self, text_widget, find_entry, repl_entry, status_var, win):
        """批量替换全部匹配"""
        keyword = find_entry.get().strip()
        repl = repl_entry.get()
        if not keyword:
            return
        positions = self._ed_find_all(text_widget, keyword)
        if not positions:
            status_var.set("未找到「%s」" % keyword)
            return
        if not messagebox.askyesno(
                "全部替换",
                f"将把全部 {len(positions)} 处「{keyword}」替换为「{repl}」，确定？",
                parent=win):
            return
        # 从后往前替换，保证位置不偏移
        for pos, end in reversed(positions):
            text_widget.delete(pos, end)
            text_widget.insert(pos, repl)
        text_widget.tag_remove("found", "1.0", tk.END)
        status_var.set("已全部替换 %d 处" % len(positions))

    def _ed_goto(self, text_widget, go_entry, status_var, win):
        """定位到第 N 条字幕"""
        try:
            n = int(go_entry.get().strip())
        except ValueError:
            messagebox.showwarning("提示", "请输入字幕条数（数字）", parent=win)
            return
        if n <= 0:
            messagebox.showwarning("提示", "条数必须大于 0", parent=win)
            return
        line_start = "1.0"
        count = 0
        end_mark = text_widget.index("end-1c")
        while text_widget.compare(line_start, "<", end_mark):
            line = text_widget.get(f"{line_start} linestart", f"{line_start} lineend")
            if line.strip() == str(n):
                self._ed_clear_hl(text_widget)
                text_widget.tag_add("found", f"{line_start} linestart", f"{line_start} lineend")
                text_widget.tag_config("found", background="#a8e6ff", foreground="black")
                text_widget.mark_set(tk.INSERT, f"{line_start} linestart")
                text_widget.see(f"{line_start} linestart")
                status_var.set("已定位到第 %d 条字幕" % n)
                return
            line_start = text_widget.index(f"{line_start} +1 line")
            count += 1
            if count > 100000:
                break
        messagebox.showinfo("未找到", "没有找到第 %d 条字幕" % n, parent=win)

    # ---------- 分类2：修改已有字幕 ----------

    def _browse_srt(self):
        """选择已有的 .srt 字幕文件"""
        path = filedialog.askopenfilename(
            title="选择字幕文件",
            filetypes=[("字幕文件", "*.srt"), ("所有文件", "*.*")],
        )
        if path:
            self.srt_file_var.set(path)

    def _open_srt_editor(self):
        """打开分类2中选择的 .srt 文件进行编辑"""
        path = self.srt_file_var.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择一个 .srt 字幕文件")
            return
        if not os.path.isfile(path):
            messagebox.showerror("错误", f"文件不存在：\n{path}")
            return
        if not path.lower().endswith(".srt"):
            messagebox.showerror("错误", "请选择 .srt 格式的字幕文件")
            return
        self._open_subtitle_editor(path)

    def _open_recent_srt(self):
        """打开最近生成的字幕文件"""
        if not self.last_srt_path or not os.path.isfile(self.last_srt_path):
            messagebox.showwarning("提示", "还没有生成过字幕，请先在「① 视频翻译字幕」里跑一次")
            return
        self._open_subtitle_editor(self.last_srt_path)


class FloatingWindow:
    """主窗口内的悬浮子窗口：可拖动、可隐藏(最小化)、可关闭，类似 Origin 的内部窗口"""

    _open_count = []  # 已打开的悬浮窗列表（用于层叠偏移）

    def __init__(self, canvas, title, width=440, height=300, x=None, y=None,
                 on_close=None, on_raise=None, icon=""):
        self.canvas = canvas
        self.title = title
        self.width = width
        self.height = height
        self.on_close = on_close
        self.on_raise = on_raise
        self._hidden = False
        self._closed = False
        self._drag_anchor = None
        self._maximized = False
        self._saved_coords = None
        self._saved_size = None
        self._pending = 0

        # 主框架
        self.frame = tk.Frame(canvas, width=width, height=height,
                              highlightthickness=1, highlightbackground="#9aa0a8")
        self.frame.pack_propagate(False)

        # 标题栏（VSCode 标签页风格：图标 + 标题 + 角标 + 按钮）
        self.title_bar = tk.Frame(self.frame, height=26)
        self.title_bar.pack(fill=tk.X)
        self.title_bar.pack_propagate(False)
        shown_title = (icon + " " + title) if icon else title
        self.title_label = tk.Label(self.title_bar, text=shown_title,
                                    font=("Microsoft YaHei UI", 9))
        self.title_label.pack(side=tk.LEFT, padx=8)

        self.close_btn = tk.Button(self.title_bar, text="✕", width=3, bd=0,
                                   command=self.close, font=("Segoe UI", 9))
        self.close_btn.pack(side=tk.RIGHT)
        self.max_btn = tk.Button(self.title_bar, text="□", width=3, bd=0,
                                 command=self._on_max_restore, font=("Segoe UI", 9))
        self.max_btn.pack(side=tk.RIGHT)
        # 角标（VSCode 风格，默认隐藏；set_badge 显示）
        self.badge = tk.Label(self.title_bar, text="", bg="#e81123", fg="white",
                              font=("Segoe UI", 8, "bold"), padx=4)

        # 内容区
        self.content = tk.Frame(self.frame)
        self.content.pack(fill=tk.BOTH, expand=True)

        # 放到画布上（层叠偏移，与顶部模块栏保持间距）
        idx = len(FloatingWindow._open_count)
        if x is None:
            x = 30 + (idx % 6) * 36
        if y is None:
            y = 42 + (idx % 6) * 30
        self.win_id = canvas.create_window(x, y, window=self.frame, anchor="nw")
        FloatingWindow._open_count.append(self)

        # 标题栏拖动 + 点击置顶
        for w in (self.title_bar, self.title_label):
            w.bind("<Button-1>", self._on_drag_start)
            w.bind("<B1-Motion>", self._on_drag_move)
        self.title_bar.bind("<Button-1>", lambda e: (self._raise(), None))

    def _on_drag_start(self, event):
        self._drag_anchor = (event.x_root, event.y_root) + tuple(self.canvas.coords(self.win_id))
        self._raise()

    def _on_drag_move(self, event):
        if self._maximized or not self._drag_anchor:
            return
        sx, sy, ox, oy = self._drag_anchor
        nx = ox + (event.x_root - sx)
        ny = oy + (event.y_root - sy)
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        nx = max(0, min(nx, cw - 30))
        ny = max(0, min(ny, ch - 24))
        self.canvas.coords(self.win_id, nx, ny)

    def _maximize(self):
        """放大到占满整个工作区"""
        if self._maximized:
            return
        self._saved_coords = self.canvas.coords(self.win_id)
        self._saved_size = (self.width, self.height)
        self._maximized = True
        self._apply_maximize_size()
        self.max_btn.configure(text="❐")

    def _apply_maximize_size(self):
        """按当前画布尺寸铺满（窗口缩放时保持占满）"""
        try:
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
            if cw <= 1:  # 未映射/启动时用配置尺寸兜底
                cw = int(self.canvas.cget("width") or self.width)
            if ch <= 1:
                ch = int(self.canvas.cget("height") or self.height)
            cw = max(cw, self.width)
            ch = max(ch, self.height)
            self.canvas.coords(self.win_id, 0, 0)
            self.canvas.itemconfigure(self.win_id, width=cw, height=ch)
            self.frame.configure(width=cw, height=ch)
        except Exception:
            pass

    def _restore(self):
        """缩小回默认大小"""
        if not self._maximized:
            return
        x, y = self._saved_coords
        w, h = self._saved_size
        try:
            self.canvas.coords(self.win_id, x, y)
            self.canvas.itemconfigure(self.win_id, width=w, height=h)
            self.frame.configure(width=w, height=h)
        except Exception:
            pass
        self._maximized = False
        self.max_btn.configure(text="□")

    def _on_max_restore(self):
        """放大/缩小切换"""
        if self._maximized:
            self._restore()
        else:
            self._maximize()

    def _raise(self):
        try:
            self.canvas.tag_raise(self.win_id)
        except Exception:
            pass
        if self.on_raise:
            try:
                self.on_raise(self)
            except Exception:
                pass

    def set_badge(self, text: str):
        """显示角标（VSCode 风格的小红标，如未读计数/未保存标记）"""
        try:
            self.badge.configure(text=text)
            if not self.badge.winfo_ismapped():
                self.badge.pack(side=tk.RIGHT, padx=(2, 0))
        except Exception:
            pass

    def clear_badge(self):
        """清除角标"""
        try:
            self._pending = 0
            self.badge.pack_forget()
            self.badge.configure(text="")
        except Exception:
            pass

    def show(self):
        """从关闭/隐藏状态恢复显示（菜单重新打开时调用）"""
        try:
            self.canvas.itemconfigure(self.win_id, state="normal")
        except Exception:
            pass
        self._hidden = False
        self._raise()

    def close(self):
        """关闭窗口"""
        if self._closed:
            return
        self._closed = True
        try:
            self.canvas.delete(self.win_id)
        except Exception:
            pass
        try:
            self.frame.destroy()
        except Exception:
            pass
        if self in FloatingWindow._open_count:
            FloatingWindow._open_count.remove(self)
        if self.on_close:
            try:
                self.on_close(self)
            except Exception:
                pass

    def apply_theme(self, T):
        """按主题设置标题栏和框架颜色"""
        try:
            self.title_bar.configure(bg=T["accent"])
            self.title_label.configure(bg=T["accent"], fg=T["accent_fg"])
            self.max_btn.configure(bg=T["accent"], fg=T["accent_fg"],
                                   activebackground=T["entry_bg"],
                                   activeforeground=T["fg"])
            self.close_btn.configure(bg=T["accent"], fg=T["accent_fg"],
                                     activebackground="#e81123",
                                     activeforeground="white")
            self.frame.configure(highlightbackground=T["hint"])
            self.content.configure(bg=T["bg"])
        except Exception:
            pass





def _acquire_single_instance() -> bool:
    """通过命名互斥体实现单实例：已有实例在运行时返回 False"""
    global _APP_MUTEX
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

        name = "VideoTranslatorStd_SingleInstance_Mutex"
        handle = kernel32.CreateMutexW(None, False, name)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            if handle:
                kernel32.CloseHandle(handle)
            return False
        _APP_MUTEX = handle
        return True
    except Exception:
        # 获取失败时不限制，避免程序无法启动
        return True


def _bring_existing_to_front() -> bool:
    """把已在运行的主窗口调到前台并还原"""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32.FindWindowW.restype = wintypes.HWND
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]

        hwnd = user32.FindWindowW(None, "视频翻译工具 - Video Translator")
        if hwnd:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def _redirect_console_to_log():
    """将 stdout/stderr 重定向到 logs/app.log，供调试终端查看"""
    try:
        log_dir = os.path.join(_app_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "app.log")
        # 日志文件过大时重新开始
        mode = "w" if (os.path.exists(log_path) and os.path.getsize(log_path) > 2 * 1024 * 1024) else "a"
        f = open(log_path, mode, encoding="utf-8", buffering=1)
        sys.stdout = f
        sys.stderr = f
    except Exception:
        pass


def main():
    # 单实例限制：整台机器（同一用户会话）只允许一个主程序窗口
    if not _acquire_single_instance():
        brought = _bring_existing_to_front()
        messagebox.showwarning(
            "程序已在运行",
            "视频翻译工具已经在运行中。\n" +
            ("已切换到现有窗口，请勿重复启动。" if brought
             else "请切换到已打开的窗口。"),
        )
        return

    # 将控制台输出写入日志文件（供"调试终端"查看），界面本身自带运行日志
    _redirect_console_to_log()

    root = tk.Tk()
    # 设置主题
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = VideoTranslatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
