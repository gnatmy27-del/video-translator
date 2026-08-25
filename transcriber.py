"""
日语语音识别模块
使用 faster-whisper 从视频/音频中识别日语语音，返回带时间戳的片段
"""

import os
import subprocess
import tempfile
from typing import Optional, Callable


def get_ffmpeg_path() -> str:
    """获取 ffmpeg 可执行文件路径（优先使用 imageio-ffmpeg 内置版本）"""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def extract_audio(video_path: str, output_path: Optional[str] = None) -> str:
    """
    从视频文件中提取音频为 16kHz 单声道 WAV（Whisper 最优输入格式）

    Args:
        video_path: 视频文件路径
        output_path: 输出 WAV 路径，为 None 时使用临时文件

    Returns:
        输出 WAV 文件路径
    """
    if output_path is None:
        output_path = os.path.join(
            tempfile.gettempdir(),
            f"jvt_audio_{os.path.splitext(os.path.basename(video_path))[0]}.wav"
        )

    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg, "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败: {result.stderr[-500:]}")

    return output_path


class JapaneseTranscriber:
    """日语语音识别器"""

    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        download_root: Optional[str] = None
    ):
        """
        Args:
            model_size: 模型大小 tiny/base/small/medium/large-v3
            device: 计算设备 auto/cpu/cuda
            compute_type: 计算精度 auto/int8/float16/float32
            download_root: 模型下载目录，为 None 时使用默认缓存
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root
        self._model = None

    def _load_model(self):
        """加载 Whisper 模型（懒加载，CUDA 不可用时自动回退 CPU）"""
        if self._model is not None:
            return

        from faster_whisper import WhisperModel

        # 预检查：Windows 下 CUDA 运行库缺失时，若直接尝试加载 GPU 模型，
        # ctranslate2 可能会长时间卡死。这里先快速检测，缺失就直接用 CPU。
        if self.device in ("auto", "cuda") and not self._cuda_dlls_available():
            print("[警告] 未检测到 CUDA 运行库（cublas/cudnn），将使用 CPU 模式")
            self.device = "cpu"
            self.compute_type = "int8"

        # 把 "auto" 解析为具体设备，方便日志显示实际运行设备
        if self.device == "auto":
            try:
                import ctranslate2
                self.device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:
                self.device = "cpu"

        kwargs = {}
        if self.device != "auto":
            kwargs["device"] = self.device
        if self.compute_type != "auto":
            kwargs["compute_type"] = self.compute_type
        if self.download_root:
            kwargs["download_root"] = self.download_root

        try:
            self._model = WhisperModel(self.model_size, **kwargs)
        except (RuntimeError, OSError) as e:
            # 创建模型时就发现 CUDA 库缺失 → 直接回退 CPU
            if self._is_cuda_error(e) and self.device != "cpu":
                self._fallback_to_cpu(e)
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            else:
                raise

    @staticmethod
    def _cuda_dlls_available() -> bool:
        """快速检查系统是否能提供 ctranslate2 所需的 CUDA 运行库（Windows）"""
        if os.name != "nt":
            return True  # 非 Windows 交给 ctranslate2 自行判断

        # 自动定位 pip 安装的 nvidia 库目录（site-packages/nvidia/xxx/bin）并加入 DLL 搜索路径
        bin_dirs = []
        try:
            import sysconfig
            site_packages = sysconfig.get_paths().get("purelib", "")
            for pkg in ("cublas", "cudnn"):
                bin_dir = os.path.join(site_packages, "nvidia", pkg, "bin")
                if os.path.isdir(bin_dir):
                    bin_dirs.append(bin_dir)
                    try:
                        os.add_dll_directory(bin_dir)
                    except Exception:
                        pass
        except Exception:
            pass

        # ctranslate2 在 Windows 上需要的主要运行库
        required = (
            "cublas64_12.dll",
            "cublasLt64_12.dll",
            "cudnn64_9.dll",
            "cudnn_ops64_9.dll",
            "cudnn_cnn64_9.dll",
        )
        import ctypes
        for dll in required:
            found = False
            # 优先用绝对路径加载
            for d in bin_dirs:
                full = os.path.join(d, dll)
                if os.path.isfile(full):
                    try:
                        ctypes.WinDLL(full)
                        found = True
                        break
                    except OSError:
                        continue
            if not found:
                try:
                    ctypes.WinDLL(dll)
                    found = True
                except OSError:
                    return False
        return True

    @staticmethod
    def _is_cuda_error(e) -> bool:
        """判断异常是否与 CUDA/GPU 库缺失有关"""
        msg = str(e).lower()
        return any(k in msg for k in (
            "cublas", "cudnn", "cuda", "dll", "cannot be loaded", "library"
        ))

    def _fallback_to_cpu(self, error):
        """切换为 CPU 模式并打印提示（会显示在界面日志中）"""
        print(f"[警告] GPU 初始化失败：{error}")
        print("[警告] 已自动切换到 CPU 模式（速度稍慢，但可以正常使用）")
        self.device = "cpu"
        self.compute_type = "int8"
        self._model = None

    def transcribe(
        self,
        media_path: str,
        language: str = "ja",
        progress_callback: Optional[Callable] = None,
        extract_audio_first: bool = True,
        vad_filter: bool = True
    ) -> list:
        """
        识别音视频中的日语语音

        Args:
            media_path: 视频或音频文件路径
            language: 语言代码，默认日语 "ja"
            progress_callback: 进度回调 callback(processed_seconds, total_seconds)
            extract_audio_first: 是否先提取音频（视频文件建议 True）
            vad_filter: 是否开启人声过滤。
                True：只识别"说话"片段，速度快、更精准，但会漏掉唱歌/带伴奏的唱段；
                False：处理全部音频，能识别唱歌，但纯音乐段落可能产生幻听文本。
                舞台剧/演唱会等含唱段的内容建议 False。

        Returns:
            片段列表，每个元素为 dict:
            - start: 开始时间（秒）
            - end: 结束时间（秒）
            - text: 识别文本
        """
        self._load_model()

        # 视频文件先提取音频
        audio_path = media_path
        temp_audio = None
        if extract_audio_first and self._is_video(media_path):
            if progress_callback:
                progress_callback(0, 0, "正在提取音频...")
            temp_audio = extract_audio(media_path)
            audio_path = temp_audio

        try:
            return self._transcribe_audio(audio_path, language, progress_callback, vad_filter)
        except RuntimeError as e:
            # CUDA 库缺失的错误往往延迟到编码阶段才抛出，这里再兜底重试一次
            if self._is_cuda_error(e) and self.device != "cpu":
                self._fallback_to_cpu(e)
                self._load_model()
                return self._transcribe_audio(audio_path, language, progress_callback, vad_filter)
            raise
        finally:
            # 清理临时音频文件
            if temp_audio and os.path.exists(temp_audio):
                try:
                    os.remove(temp_audio)
                except OSError:
                    pass

    def _transcribe_audio(self, audio_path: str, language: str,
                          progress_callback: Optional[Callable],
                          vad_filter: bool = True) -> list:
        """实际执行转写（在已加载好的模型上运行）"""
        if vad_filter:
            segments, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    threshold=0.4,        # 放宽人声阈值，减少漏掉说话/轻声
                    min_speech_duration_ms=200,
                    speech_pad_ms=300,
                ),
            )
        else:
            # 关闭人声过滤：处理全部音频，可捕捉唱歌/唱段
            segments, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=False,
                no_speech_threshold=0.6,  # 纯音乐/无歌词段落仍会被跳过
            )

        total_duration = info.duration if info else 0
        results = []

        for seg in segments:
            results.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
            })
            if progress_callback and total_duration > 0:
                progress_callback(seg.end, total_duration, f"识别中... {seg.end:.0f}s / {total_duration:.0f}s")

        return results

    @staticmethod
    def _is_video(filepath: str) -> bool:
        """判断是否为视频文件"""
        video_exts = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm", ".m4v", ".ts"}
        ext = os.path.splitext(filepath)[1].lower()
        return ext in video_exts
