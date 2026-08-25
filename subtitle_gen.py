"""
SRT 字幕生成模块
将识别+翻译结果转换为标准 .srt 字幕文件
"""

import os
from datetime import timedelta


def format_timestamp(seconds: float) -> str:
    """将秒数转换为 SRT 时间戳格式 HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: list, output_path: str, bilingual: bool = True) -> str:
    """
    生成 SRT 字幕文件

    Args:
        segments: 列表，每个元素为 dict，包含:
            - start: 开始时间（秒）
            - end: 结束时间（秒）
            - text: 日语文本
            - translation: 中文翻译（可选）
        output_path: 输出 .srt 文件路径
        bilingual: 是否双语字幕（日文在上，中文在下）

    Returns:
        输出文件路径
    """
    lines = []
    for i, seg in enumerate(segments, start=1):
        start_ts = format_timestamp(seg.get("start", 0))
        end_ts = format_timestamp(seg.get("end", 0))
        japanese = seg.get("text", "").strip()
        translation = seg.get("translation", "").strip()

        lines.append(str(i))
        lines.append(f"{start_ts} --> {end_ts}")

        if bilingual and translation:
            lines.append(japanese)
            lines.append(translation)
        elif translation:
            lines.append(translation)
        else:
            lines.append(japanese)

        lines.append("")  # 空行分隔

    content = "\n".join(lines)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path
