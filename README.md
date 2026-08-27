# 🎬 视频翻译工具（多语言）

![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
[![GitHub Release](https://img.shields.io/github/v/release/gnatmy27-del/video-translator)](https://github.com/gnatmy27-del/video-translator/releases)
[![Stars](https://img.shields.io/github/stars/gnatmy27-del/video-translator)](https://github.com/gnatmy27-del/video-translator)

把任意语言的视频自动转成字幕（`.srt` 文件），用 PotPlayer / VLC / 剪映等任意播放器加载字幕即可观看。

**完全免费、开源、无需上传视频，隐私安全**。支持识别日语/英语/韩语/中文/粤语/法语/德语/西班牙语/俄语等 15 种语言，可翻译成中文/英语/日语/韩语等 11 种目标语言。

## 📥 下载（免安装版，推荐新手）

不想装 Python？直接下载**免安装 exe**，解压双击就能用：

| 版本 | 下载 | 说明 |
|---|---|---|
| 🖥️ **Windows 免安装版** | [⬇️ video-translator-v1.0.0-windows-x64.zip](https://github.com/gnatmy27-del/video-translator/releases/latest) | 约 186MB。**双击即用，不需要安装任何东西**，适合所有人 |
| 📦 源码版 | [⬇️ video-translator-v1.0.0-source.zip](https://github.com/gnatmy27-del/video-translator/releases/latest) | 适合有 Python 的开发者 |

**免安装版使用**：解压 → 双击 `video-translator.exe` → 选视频 → 开始翻译。

> ⚠️ 首次运行若提示「Windows 已保护你的电脑」，点 **更多信息 → 仍要运行** 即可（程序没有数字签名，属正常现象）。
> 💡 翻译质量最好用 **DeepSeek AI**（免费注册、几毛钱一部电影），详见下方「常见问题」。

---

## 如果觉得好用
**点个 ⭐ Star、分享给需要的人**，就是对我最大的支持！❤️

---

## 功能

- 🎙️ **多语言语音识别**：基于 Whisper 模型，支持 15 种语言（日/英/韩/中/法/德/西/俄等）
- 🌐 **多语言翻译**：任意源语言 → 中/英/日/韩/法/德/西/俄等目标语言，支持双语字幕
- ✍️ **内置字幕编辑器**：查找/替换/批量替换/定位到第N条，随时微调翻译
- 🎤 **唱歌/音乐模式**：识别舞台剧、演唱会中的唱段
- 💻 **图形界面**：点点鼠标就能用，不需要敲命令
- 🔒 **纯本地运行**：视频不上传，只在翻译时联网调用翻译接口

---

## 安装（只需一次）

### 前置要求
- Windows 10/11
- Python 3.10 ~ 3.12（**推荐 3.11**，3.13 部分包可能兼容性有问题）
- 内存至少 4GB（推荐 8GB 以上）

> 还没装 Python？去 https://www.python.org/downloads/ 下载，**安装时一定要勾选 "Add Python to PATH"**。

### 安装步骤
1. 打开本文件夹
2. 双击 `install.bat`
3. 等待安装完成（首次需要下载模型依赖，约几分钟）

> 如果安装失败，大概率是网络问题。可以设置代理后重试，或手动执行：
> ```
> python -m pip install -r requirements.txt
> ```

---

## 使用方法

程序分三个功能页签，互不依赖，可自由切换：

**① 视频翻译字幕**：完整流程 —— 选视频 → 识别语音 → 翻译 → 生成 SRT 字幕
**② 修改已有字幕**：直接打开已有的 `.srt` 文件微调翻译（不需要先跑翻译流程）
**③ 设置**：外观主题 / 运行日志

### ① 视频翻译字幕

1. 双击 `run.bat` 启动工具
2. **① 选择视频文件**：点击"浏览"选择要翻译的日语视频
3. **② 识别设置**：
   - **模型大小**：默认 `small` 即可，日语识别效果不错；电脑配置好可以选 `medium` 或 `large-v3`，更准但更慢
   - **计算设备**：有 NVIDIA 显卡选 `CUDA`，速度快很多；没有就选 `CPU` 或 `自动`
4. **③ 翻译与输出**：
   - 勾选"翻译成中文"
   - 勾选"双语字幕"（日文+中文同时显示，学日语神器）
   - 选择字幕文件保存位置（默认和视频同目录）
5. 点击 **▶ 开始翻译**
6. 等待完成，日志里会显示字幕文件路径

> ⚠️ **首次使用**会自动下载 Whisper 模型（small 约 460MB），请耐心等待。之后再用就不需要下载了。

---

## 怎么看字幕

生成的 `.srt` 字幕文件和视频放在一起，文件名相同（只是后缀不同）。

- **PotPlayer**：打开视频后自动加载同名字幕，或拖入字幕文件
- **VLC**：视频 → 字幕轨道 → 添加字幕文件
- **剪映 / PR**：导入字幕文件即可编辑
- **手机播放**：把 `.srt` 和视频放同一目录，用 MX Player 等播放器打开

---

## 模型选择建议

| 模型 | 大小 | 速度 | 日语准确率 | 适用场景 |
|------|------|------|-----------|---------|
| tiny | 75MB | 极快 | 一般 | 快速预览、短句 |
| base | 145MB | 快 | 尚可 | 日常使用 |
| **small** | **460MB** | **中等** | **不错** | **推荐默认** |
| medium | 1.5GB | 慢 | 好 | 舞台剧、访谈等长对白 |
| large-v3 | 3GB | 很慢 | 最好 | 追求最高质量 |

> 模型文件会自动下载到系统缓存目录，卸载工具时如需清理可删除 `C:\Users\你的用户名\.cache\huggingface`。

---

## 常见问题

### Q: 翻译失败 / 翻译结果为空？翻译质量不好？
A: 程序默认用免费在线翻译（MyMemory），国内网络可用但质量一般、长视频有字符限额。
**推荐使用 DeepSeek AI 翻译**（质量高、容错强，能处理语音识别偏差）：
1. 打开 https://platform.deepseek.com 注册，创建 API Key
2. 在程序界面的「③ 翻译与输出设置」里粘贴 API Key，点「保存」
3. 之后翻译自动走 DeepSeek（约每部电影几毛钱），留空则用免费翻译

> 💡 **视频背景描述**：在「③ 翻译与输出设置」底部可以填写视频背景
> （如"这是XX舞台剧，主角是奥斯卡，发生在18世纪法国"），
> DeepSeek 会结合背景理解剧情、人名和专有名词，翻译更准确。

> 免费翻译在国内基本不可用的原因：Google 翻译接口被限流/屏蔽，有道接口已加反爬。

### Q: 提示 "Library cublas64_12.dll is not found or cannot be loaded"？
A: 程序尝试用 NVIDIA 显卡（GPU/CUDA）加速，但电脑缺少 CUDA 运行库。
- **现在程序已自动处理**：检测到缺少 CUDA 库时会自动改用 CPU 模式继续运行，不会报错卡死。
- 如果想让 GPU 真正跑起来（速度快很多），见下方「开启 GPU 加速」。

### Q: 怎么让 RTX 显卡参与加速？程序还是有点慢
A: 有 NVIDIA 显卡的话，安装 CUDA 运行库即可（约 1.1GB，一次性下载）：
```
python -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```
- 国内网络慢可加镜像源：`-i https://pypi.tuna.tsinghua.edu.cn/simple`
- 安装后直接用 `run.bat` 启动即可（会自动加载 CUDA 库），设备选「自动」就会优先用显卡
- ⚠️ 注意：RTX 50 系列（Blackwell 架构）不支持 int8 量化，程序会自动用 float16，属正常现象

### Q: 速度很慢怎么办？
- 选更小的模型（small → base → tiny）
- 有 NVIDIA 显卡选 CUDA
- 关闭其他占用内存的程序

### Q: 唱歌/唱段没被识别出来？(舞台剧、演唱会)
A: 程序默认的"人声过滤"只识别说话片段，唱歌（尤其带伴奏的唱段）常被当作非人声丢弃。
解决：在「② 语音识别设置」勾选 **"☑ 包含唱歌/音乐段落"**，会关闭人声过滤、处理全部音频。
注意：开启后识别更全面但稍慢，纯音乐段落可能产生少量无意义文本（可在字幕里手动删掉）。

### Q: Python 3.13 安装依赖报错？
A: 部分依赖包可能还不支持 Python 3.13。建议安装 Python 3.11（最稳定），安装时勾选 Add to PATH。

---

## 项目结构

```
japanese-video-translator/
├── main.py               # 主程序（图形界面）
├── transcriber.py        # 语音识别模块
├── translator.py         # 翻译模块
├── subtitle_gen.py       # 字幕生成模块
├── requirements.txt      # 依赖列表
├── config.example.json   # 配置示例（复制为 config.json 使用）
├── install.bat           # 一键安装
├── run.bat               # 一键运行
└── README.md             # 本说明
```

## 配置说明

- 程序首次运行会自动生成 `config.json`（不会提交到仓库，见 `.gitignore`）
- `config.example.json` 是配置模板；把 `config.json` 里的 `deepseek_api_key` 填上你的 Key 即可使用 DeepSeek AI 翻译（质量最高、容错强）
- 也可以在程序界面「③ 翻译与输出设置」里直接粘贴 API Key 并点「保存」

## 开源协议

本项目基于 **MIT License** 开源，可自由使用、修改、分发（详见 `LICENSE`）。

## 免责声明

- 语音识别基于 OpenAI Whisper（开源）；翻译使用 DeepSeek / MyMemory / Google 等在线接口
- 请尊重版权，仅翻译你有权观看的内容
- 本工具仅供学习与个人使用
