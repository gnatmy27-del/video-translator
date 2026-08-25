"""
多语言字幕翻译模块

支持后端（按优先级）：
1. DeepSeek AI（推荐）：容错高，适合语音识别产生的"模糊文本"，需要 API Key
2. MyMemory：免费、无需注册，国内可用
3. Google：免费，但国内网络不稳定/易被限流
"""

import json
import os
import time
from typing import Optional, List

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 源语言（语音识别 + 翻译源）：显示名 -> 各后端代码
SOURCE_LANGUAGES = {
    "日语":     {"whisper": "ja",   "google": "ja",    "mymemory": "ja-JP"},
    "英语":     {"whisper": "en",   "google": "en",    "mymemory": "en-GB"},
    "韩语":     {"whisper": "ko",   "google": "ko",    "mymemory": "ko-KR"},
    "中文":     {"whisper": "zh",   "google": "zh-CN", "mymemory": "zh-CN"},
    "粤语":     {"whisper": "yue",  "google": "yue",   "mymemory": "zh-HK"},
    "法语":     {"whisper": "fr",   "google": "fr",    "mymemory": "fr-FR"},
    "德语":     {"whisper": "de",   "google": "de",    "mymemory": "de-DE"},
    "西班牙语": {"whisper": "es",   "google": "es",    "mymemory": "es-ES"},
    "俄语":     {"whisper": "ru",   "google": "ru",    "mymemory": "ru-RU"},
    "意大利语": {"whisper": "it",   "google": "it",    "mymemory": "it-IT"},
    "葡萄牙语": {"whisper": "pt",   "google": "pt",    "mymemory": "pt-PT"},
    "泰语":     {"whisper": "th",   "google": "th",    "mymemory": "th-TH"},
    "越南语":   {"whisper": "vi",   "google": "vi",    "mymemory": "vi-VN"},
    "印尼语":   {"whisper": "id",   "google": "id",    "mymemory": "id-ID"},
    "阿拉伯语": {"whisper": "ar",   "google": "ar",    "mymemory": "ar-SA"},
}

# 目标语言（翻译成什么）：显示名 -> 各后端代码
TARGET_LANGUAGES = {
    "中文(简体)": {"google": "zh-CN", "mymemory": "zh-CN"},
    "中文(繁体)": {"google": "zh-TW", "mymemory": "zh-TW"},
    "英语":       {"google": "en",    "mymemory": "en-GB"},
    "日语":       {"google": "ja",    "mymemory": "ja-JP"},
    "韩语":       {"google": "ko",    "mymemory": "ko-KR"},
    "法语":       {"google": "fr",    "mymemory": "fr-FR"},
    "德语":       {"google": "de",    "mymemory": "de-DE"},
    "西班牙语":   {"google": "es",    "mymemory": "es-ES"},
    "俄语":       {"google": "ru",    "mymemory": "ru-RU"},
    "意大利语":   {"google": "it",    "mymemory": "it-IT"},
    "泰语":       {"google": "th",    "mymemory": "th-TH"},
}


class Translator:
    """翻译器，支持 DeepSeek / MyMemory / Google 多后端"""

    def __init__(self, backend: str = "auto", proxy: Optional[str] = None,
                 api_key: Optional[str] = None, context: Optional[str] = None,
                 source_lang: str = "日语", target_lang: str = "中文(简体)"):
        """
        Args:
            backend: 后端策略，"auto" = DeepSeek(有key时) → MyMemory → Google
            proxy: 代理地址，如 "http://127.0.0.1:7890"（仅 Google 用）
            api_key: DeepSeek API Key，未传时自动读取 config.json 或环境变量
            context: 视频背景描述（如剧情、人名、设定等），帮助 AI 更准确翻译
            source_lang: 源语言显示名（见 SOURCE_LANGUAGES）
            target_lang: 目标语言显示名（见 TARGET_LANGUAGES）
        """
        self.backend = backend
        self.proxy = proxy
        self.context = (context or "").strip()
        self.source_lang = SOURCE_LANGUAGES.get(source_lang, SOURCE_LANGUAGES["日语"])
        self.target_lang = TARGET_LANGUAGES.get(target_lang, TARGET_LANGUAGES["中文(简体)"])
        self.source_lang_name = source_lang
        self.target_lang_name = target_lang
        self._google = None
        self._mymemory = None

        # DeepSeek API Key 来源：参数 > 环境变量 > config.json
        self._deepseek_key = (api_key or os.environ.get("DEEPSEEK_API_KEY") or "").strip()
        if not self._deepseek_key:
            self._deepseek_key = (self._load_key_from_config() or "").strip()

        self._system_prompt = self._build_system_prompt()
        self._init_engines()

    def _build_system_prompt(self) -> str:
        """构建 DeepSeek 系统提示词（语言对 + 可选的视频背景描述）"""
        prompt = (
            f"你是一名专业的{self.source_lang_name}→{self.target_lang_name}字幕翻译。"
            f"用户提供的{self.source_lang_name}文本来自语音识别，"
            "可能存在同音错字、缺字、噪声乱码等情况，请结合上下文推断真实含义，"
            f"翻译成通顺自然的{self.target_lang_name}。"
            "只输出译文，不要添加任何解释或多余内容。\n"
            "当用户输入一个 JSON 字符串数组（每条一句原文）时，请将数组中的每一条"
            f"翻译成{self.target_lang_name}，并输出一个同样长度的 JSON 字符串数组，"
            "顺序与输入一致，不要输出其他内容。"
        )
        if self.context:
            prompt += (
                "\n\n另外，用户提供了以下视频的背景信息，"
                "请结合它来理解剧情、人名、专有名词和台词含义：\n"
                f"<背景>\n{self.context}\n</背景>"
            )
        return prompt

    # ---------- 初始化 ----------

    @staticmethod
    def _load_key_from_config() -> Optional[str]:
        """从项目目录的 config.json 读取 deepseek_api_key"""
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "config.json")
            if os.path.exists(config_path):
                with open(config_path, encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("deepseek_api_key") or None
        except Exception:
            pass
        return None

    def _init_engines(self):
        """初始化免费翻译引擎（Google + MyMemory），按所选语言对配置"""
        # 给所有网络请求设置超时，避免免费接口慢/挂起时程序卡死
        try:
            import socket
            socket.setdefaulttimeout(20)
        except Exception:
            pass

        try:
            from deep_translator import GoogleTranslator
            self._google = GoogleTranslator(
                source=self.source_lang["google"],
                target=self.target_lang["google"],
                proxy=self.proxy,
            )
        except Exception as e:
            print(f"[警告] Google 翻译引擎初始化失败: {e}")

        try:
            from deep_translator import MyMemoryTranslator
            self._mymemory = MyMemoryTranslator(
                source=self.source_lang["mymemory"],
                target=self.target_lang["mymemory"],
            )
        except Exception as e:
            print(f"[警告] MyMemory 翻译引擎初始化失败: {e}")

    @property
    def has_deepseek(self) -> bool:
        """是否配置了 DeepSeek API Key"""
        return bool(self._deepseek_key)


    def translate(self, text: str) -> str:
        """翻译单条文本，失败返回空字符串"""
        if not text or not text.strip():
            return ""
        if self.has_deepseek:
            try:
                return self._deepseek_translate([text])[0]
            except Exception as e:
                print(f"[翻译失败 deepseek] {text[:30]}... -> {e}")
        return self._translate_free(text)

    def translate_batch(self, texts: list, progress_callback=None) -> list:
        """
        批量翻译

        Args:
            texts: 日语句子列表
            progress_callback: 进度回调 callback(current, total)

        Returns:
            中文翻译列表（失败项为空字符串）
        """
        if not texts:
            return []
        total = len(texts)

        # DeepSeek：批量调用，一次翻译多条
        if self.has_deepseek:
            return self._translate_batch_deepseek(texts, total, progress_callback)

        # 免费后端：逐条翻译
        return self._translate_batch_free(texts, total, progress_callback)

    def _translate_batch_deepseek(self, texts: list, total: int,
                                  progress_callback=None) -> list:
        """DeepSeek 批量翻译：每批 15 条"""
        results = [""] * total
        batch_size = 15
        for start in range(0, total, batch_size):
            batch = texts[start:start + batch_size]
            done = False
            try:
                translated = self._deepseek_translate(batch)
                if len(translated) == len(batch):
                    results[start:start + len(batch)] = translated
                    done = True
            except Exception as e:
                print(f"[批量翻译失败] 第{start + 1}-{start + len(batch)}条 -> {e}")

            if not done:
                # 批量失败，逐条重试，再不行用免费后端兜底
                for i, txt in enumerate(batch):
                    if not txt or not txt.strip():
                        continue
                    try:
                        results[start + i] = self._deepseek_translate([txt])[0]
                    except Exception as e2:
                        print(f"[翻译失败 deepseek] {txt[:30]}... -> {e2}")
                        results[start + i] = self._translate_free(txt)
                    time.sleep(0.1)

            if progress_callback:
                progress_callback(min(start + batch_size, total), total)
            time.sleep(0.2)  # 避免触发限流
        return results

    def _deepseek_translate(self, texts: list) -> list:
        """调用 DeepSeek 批量翻译（输入输出均为字符串列表）"""
        import requests

        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": json.dumps(texts, ensure_ascii=False)},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self._deepseek_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(
                f"DeepSeek API HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        # 优先按 JSON 数组解析
        parsed = self._parse_json_list(content)
        if parsed and len(parsed) == len(texts):
            return parsed

        # 退而求其次：按行解析
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        if len(lines) == len(texts):
            return lines

        raise ValueError(f"DeepSeek 返回格式无法解析: {content[:200]}")

    @staticmethod
    def _parse_json_list(content: str) -> Optional[list]:
        """尝试把模型输出解析为 JSON 字符串数组"""
        text = content.strip()
        # 去掉可能的 markdown 代码块围栏
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [str(x).strip() for x in data]
        except Exception:
            pass
        return None

    def _translate_batch_free(self, texts: list, total: int,
                              progress_callback=None) -> list:
        """免费后端逐条翻译（MyMemory 优先）"""
        results = []
        for i, text in enumerate(texts):
            results.append(self._translate_free(text))
            if progress_callback:
                progress_callback(i + 1, total, text)
            # 免费接口限速：MyMemory 约 2 次/秒
            time.sleep(0.5)
        return results

    def _translate_free(self, text: str) -> str:
        """用免费后端翻译单条（MyMemory 优先，Google 兜底）"""
        if not text or not text.strip():
            return ""
        for name, engine in self._free_engines():
            for attempt in range(2):
                try:
                    result = engine.translate(text.strip())
                    if result and result.strip():
                        return result.strip()
                except Exception as e:
                    if attempt < 1:
                        time.sleep(1 + attempt)
                    else:
                        print(f"[翻译失败 {name}] {text[:30]}... -> {e}")
        return ""

    def _free_engines(self) -> list:
        """按优先级返回可用的免费引擎（MyMemory 在国内更稳定，放前面）"""
        engines = []
        if self._mymemory:
            engines.append(("mymemory", self._mymemory))
        if self._google:
            engines.append(("google", self._google))
        return engines

