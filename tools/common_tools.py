from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

from tools.base import FileType, ToolValidationError


# =========================
# 基础目录 / 文件检查
# =========================

def ensure_dir(path: str) -> Path:
    """确保目录存在，不存在则创建。"""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def ensure_parent_dir(file_path: str) -> Path:
    """确保文件的父目录存在。"""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.parent


def ensure_file_exists(file_path: str) -> Path:
    """确保文件存在且是普通文件。"""
    path = Path(file_path)
    if not path.exists():
        raise ToolValidationError(f"File not found: {file_path}")
    if not path.is_file():
        raise ToolValidationError(f"Path is not a file: {file_path}")
    return path


def ensure_excel_file(file_path: str) -> Path:
    """确保 Excel 文件存在且扩展名受支持。"""
    try:
        path = ensure_file_exists(file_path)
    except ToolValidationError as exc:
        if str(exc).startswith("File not found:"):
            raise ToolValidationError(f"Excel file not found: {file_path}") from exc
        raise

    ext = get_file_extension(file_path)
    supported = (".xlsx", ".xlsm")
    if ext not in supported:
        raise ToolValidationError(
            f"Unsupported Excel file extension: {ext}. "
            f"Expected one of: {supported}"
        )
    return path


def ensure_files_exist(file_paths: Iterable[str]) -> list[Path]:
    """批量检查文件是否存在。"""
    return [ensure_file_exists(p) for p in file_paths]


# =========================
# 文件类型 / 扩展名
# =========================

def get_file_extension(file_path: str) -> str:
    """返回小写扩展名，例如 .docx / .xlsx。"""
    return Path(file_path).suffix.lower()


def get_file_stem(file_path: str) -> str:
    """返回不带扩展名的文件名。"""
    return Path(file_path).stem


def get_file_name(file_path: str) -> str:
    """返回文件名（含扩展名）。"""
    return Path(file_path).name


def detect_file_type(file_path: str) -> FileType:
    """根据扩展名识别抽象文件类型。"""
    ext = get_file_extension(file_path)

    if ext in {".doc", ".docx"}:
        return FileType.WORD
    if ext in {".xls", ".xlsx", ".xlsm", ".csv"}:
        return FileType.EXCEL if ext != ".csv" else FileType.CSV
    if ext in {".ppt", ".pptx"}:
        return FileType.PPT
    if ext == ".pdf":
        return FileType.PDF
    if ext in {".txt", ".md"}:
        return FileType.TEXT
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        return FileType.IMAGE
    if ext in {".zip", ".rar", ".7z"}:
        return FileType.ARCHIVE

    return FileType.UNKNOWN


# =========================
# 输出文件名 / 路径生成
# =========================

def sanitize_filename(name: str) -> str:
    """简单清洗文件名，避免明显非法字符。"""
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    result = name
    for ch in illegal_chars:
        result = result.replace(ch, "_")
    return result.strip() or "untitled"


def make_output_filename(
    original_name: str,
    tag: str,
    new_extension: Optional[str] = None,
) -> str:
    """基于原文件名生成输出文件名。

    示例：
    - template.docx + filled -> template_filled.docx
    - data.xlsx + inspected -> data_inspected.xlsx
    """
    path = Path(original_name)
    stem = sanitize_filename(path.stem)
    suffix = new_extension if new_extension is not None else path.suffix

    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"

    tag = sanitize_filename(tag)
    return f"{stem}_{tag}{suffix}"


def make_timestamped_filename(
    original_name: str,
    tag: str,
    new_extension: Optional[str] = None,
) -> str:
    """生成带时间戳的输出文件名。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(original_name)
    stem = sanitize_filename(path.stem)
    suffix = new_extension if new_extension is not None else path.suffix

    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"

    tag = sanitize_filename(tag)
    return f"{stem}_{tag}_{timestamp}{suffix}"


def build_output_path(
    output_dir: str,
    original_name: str,
    tag: str,
    new_extension: Optional[str] = None,
    use_timestamp: bool = False,
) -> str:
    """构造输出文件完整路径。"""
    ensure_dir(output_dir)

    if use_timestamp:
        filename = make_timestamped_filename(
            original_name=original_name,
            tag=tag,
            new_extension=new_extension,
        )
    else:
        filename = make_output_filename(
            original_name=original_name,
            tag=tag,
            new_extension=new_extension,
        )

    return str(Path(output_dir) / filename)


def build_temp_path(
    temp_dir: str,
    prefix: str = "tmp",
    extension: str = "",
) -> str:
    """生成临时文件路径，不实际创建文件。"""
    ensure_dir(temp_dir)

    ext = extension.strip()
    if ext and not ext.startswith("."):
        ext = f".{ext}"

    unique_id = uuid.uuid4().hex[:12]
    prefix = sanitize_filename(prefix)
    filename = f"{prefix}_{unique_id}{ext}"
    return str(Path(temp_dir) / filename)


# =========================
# 文件复制 / 移动 / 删除
# =========================

def copy_file_to(src_path: str, dst_path: str) -> str:
    """复制文件到目标路径。"""
    ensure_file_exists(src_path)
    ensure_parent_dir(dst_path)
    shutil.copy2(src_path, dst_path)
    return dst_path


def move_file_to(src_path: str, dst_path: str) -> str:
    """移动文件到目标路径。"""
    ensure_file_exists(src_path)
    ensure_parent_dir(dst_path)
    shutil.move(src_path, dst_path)
    return dst_path


def delete_file_if_exists(file_path: str) -> bool:
    """删除文件，存在则删，不存在返回 False。"""
    path = Path(file_path)
    if path.exists() and path.is_file():
        path.unlink()
        return True
    return False


# =========================
# 文件元信息
# =========================

def get_file_size(file_path: str) -> int:
    """返回文件大小（字节）。"""
    path = ensure_file_exists(file_path)
    return path.stat().st_size


def get_file_metadata(file_path: str) -> dict[str, Any]:
    """返回基础文件元信息。"""
    path = ensure_file_exists(file_path)
    stat = path.stat()

    return {
        "file_path": str(path),
        "file_name": path.name,
        "stem": path.stem,
        "extension": path.suffix.lower(),
        "file_type": detect_file_type(str(path)).value,
        "size": stat.st_size,
        "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


# =========================
# 简单文本日志
# =========================

def write_text(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """覆盖写入文本。"""
    ensure_parent_dir(file_path)
    Path(file_path).write_text(content, encoding=encoding)
    return file_path


def append_text(file_path: str, content: str, encoding: str = "utf-8") -> str:
    """追加写入文本。"""
    ensure_parent_dir(file_path)
    with open(file_path, "a", encoding=encoding) as f:
        f.write(content)
    return file_path


def write_lines_to_file(
    file_path: str,
    lines: list[str],
    encoding: str = "utf-8",
    newline: str = "\n",
) -> str:
    """覆盖写入多行文本。"""
    ensure_parent_dir(file_path)
    content = newline.join(lines)
    Path(file_path).write_text(content, encoding=encoding)
    return file_path


def append_line_to_file(
    file_path: str,
    line: str,
    encoding: str = "utf-8",
) -> str:
    """追加一行文本。"""
    ensure_parent_dir(file_path)
    with open(file_path, "a", encoding=encoding) as f:
        f.write(line + "\n")
    return file_path


# =========================
# 常用辅助
# =========================

def ensure_allowed_extension(file_path: str, allowed_extensions: tuple[str, ...]) -> None:
    """检查扩展名是否在允许列表中。"""
    ext = get_file_extension(file_path)
    normalized = tuple(e.lower() for e in allowed_extensions)
    if ext not in normalized:
        raise ToolValidationError(
            f"Unsupported file extension: {ext}. Expected one of: {normalized}"
        )


def choose_first_existing_path(paths: Iterable[str]) -> Optional[str]:
    """从多个路径中返回第一个存在的路径。"""
    for path in paths:
        if Path(path).exists():
            return path
    return None


def with_suffix(file_path: str, new_extension: str) -> str:
    """替换文件扩展名。"""
    path = Path(file_path)
    ext = new_extension if new_extension.startswith(".") else f".{new_extension}"
    return str(path.with_suffix(ext))