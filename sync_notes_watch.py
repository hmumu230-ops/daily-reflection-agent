"""
笔记自动监听同步脚本
后台运行，检测到桌面「每日笔记」文件夹有变化时自动同步到 GitHub
用法: python sync_notes_watch.py
"""

import os
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

NOTES_FOLDER = Path.home() / 'Desktop' / '每日笔记'
REPO_DIR = Path.home() / 'Desktop' / '每日反思智能体'
NOTES_REPO_DIR = REPO_DIR / 'notes'
CHECK_INTERVAL = 30  # 每 30 秒检查一次

SUPPORTED_EXTS = {'.txt', '.md', '.xmind', '.mm'}


def get_today():
    return date.today().isoformat()


def ensure_dirs():
    NOTES_FOLDER.mkdir(exist_ok=True)
    NOTES_REPO_DIR.mkdir(exist_ok=True)


def get_source_files():
    """获取桌面笔记文件夹中支持的文件"""
    if not NOTES_FOLDER.exists():
        return []
    return [f for f in NOTES_FOLDER.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]


def sync_once():
    """执行一次同步"""
    today = get_today()
    today_dir = NOTES_REPO_DIR / today
    today_dir.mkdir(exist_ok=True)

    files = get_source_files()
    if not files:
        return False

    copied = 0
    for f in files:
        dest = today_dir / f.name
        # 只在文件更新时复制
        if not dest.exists() or f.stat().st_mtime > dest.stat().st_mtime:
            shutil.copy2(f, dest)
            copied += 1
            print(f'  复制: {f.name}')

    if copied == 0:
        return False

    # Git commit + push
    try:
        subprocess.run(['git', 'add', 'notes/'], cwd=REPO_DIR, capture_output=True)
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=REPO_DIR, capture_output=True
        )
        if result.returncode != 0:  # 有变更
            subprocess.run(
                ['git', 'commit', '-m', f'notes: sync {today} 学习笔记'],
                cwd=REPO_DIR, capture_output=True
            )
            push_result = subprocess.run(
                ['git', 'push', 'origin', 'main'],
                cwd=REPO_DIR, capture_output=True, text=True
            )
            if push_result.returncode == 0:
                print(f'[{today}] 已同步 {copied} 个文件到 GitHub')
            else:
                print(f'[{today}] 本地已提交，推送失败: {push_result.stderr.strip()}')
            return True
    except Exception as e:
        print(f'[{today}] Git 操作失败: {e}')

    return False


def main():
    ensure_dirs()
    print(f'笔记监听已启动')
    print(f'监听文件夹: {NOTES_FOLDER}')
    print(f'支持格式: {", ".join(SUPPORTED_EXTS)}')
    print(f'每 {CHECK_INTERVAL} 秒检查一次，按 Ctrl+C 停止\n')

    while True:
        try:
            sync_once()
        except Exception as e:
            print(f'同步出错: {e}')
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
