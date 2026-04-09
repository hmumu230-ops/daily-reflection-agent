"""
笔记同步服务：从 GitHub 仓库的 notes/ 文件夹读取用户笔记
支持格式：.txt .md .xmind .mm
只读取，不修改任何文件
"""

import requests
import zipfile
import io
import json
import base64
import xml.etree.ElementTree as ET
from config import GITHUB_TOKEN, GITHUB_REPO, NOTES_DIR


def _github_headers():
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers


def _api_get(path):
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
    r = requests.get(url, headers=_github_headers(), timeout=10)
    if r.status_code == 200:
        return r.json()
    return None


def _fetch_raw(download_url):
    r = requests.get(download_url, timeout=15)
    return r.content if r.status_code == 200 else b''


# ===== 各格式文本提取 =====

def _extract_txt(raw: bytes) -> str:
    return raw.decode('utf-8', errors='ignore').strip()


def _extract_md(raw: bytes) -> str:
    return raw.decode('utf-8', errors='ignore').strip()


def _extract_xmind(raw: bytes) -> str:
    """XMind 文件是 ZIP，解析 content.json 或 content.xml"""
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = z.namelist()

            # 新版 XMind：content.json
            if 'content.json' in names:
                data = json.loads(z.read('content.json'))
                texts = []
                def walk(node):
                    if isinstance(node, dict):
                        if 'title' in node:
                            texts.append(node['title'])
                        for child in node.get('children', {}).get('attached', []):
                            walk(child)
                        for child in node.get('children', {}).get('detached', []):
                            walk(child)
                    elif isinstance(node, list):
                        for item in node:
                            walk(item)
                walk(data)
                return '\n'.join(t for t in texts if t.strip())

            # 旧版 XMind：content.xml
            if 'content.xml' in names:
                xml_str = z.read('content.xml')
                return _parse_xmind_xml(xml_str)

    except Exception as e:
        return f'[XMind 解析失败: {e}]'
    return ''


def _parse_xmind_xml(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
        ns = {'xmind': 'urn:xmind:xmap:xmlns:content:2.0'}
        texts = []
        for topic in root.iter():
            title = topic.get('xlink:title') or topic.findtext('{urn:xmind:xmap:xmlns:content:2.0}title')
            if title and title.strip():
                texts.append(title.strip())
        return '\n'.join(texts)
    except Exception as e:
        return f'[XMind XML 解析失败: {e}]'


def _extract_mm(raw: bytes) -> str:
    """FreeMind .mm 格式，标准 XML"""
    try:
        root = ET.fromstring(raw)
        texts = []
        for node in root.iter('node'):
            text = node.get('TEXT', '').strip()
            if text:
                texts.append(text)
        return '\n'.join(texts)
    except Exception as e:
        return f'[思维导图解析失败: {e}]'


def _extract_content(filename: str, raw: bytes) -> str:
    name = filename.lower()
    if name.endswith('.txt'):
        return _extract_txt(raw)
    elif name.endswith('.md'):
        return _extract_md(raw)
    elif name.endswith('.xmind'):
        return _extract_xmind(raw)
    elif name.endswith('.mm'):
        return _extract_mm(raw)
    return ''   # 不支持的格式跳过


# ===== 对外接口 =====

def fetch_notes_for_date(date_str: str) -> list:
    """
    获取某天的所有笔记文件，返回 [{name, text}, ...]
    date_str 格式: '2026-04-09'
    """
    if not GITHUB_TOKEN:
        return []

    items = _api_get(f'{NOTES_DIR}/{date_str}')
    if not items or not isinstance(items, list):
        return []

    results = []
    for item in items:
        if item.get('type') != 'file':
            continue
        filename = item['name']
        download_url = item.get('download_url', '')
        if not download_url:
            continue

        raw = _fetch_raw(download_url)
        if not raw:
            continue

        text = _extract_content(filename, raw)
        if text.strip():
            results.append({'name': filename, 'text': text})

    return results


def fetch_notes_for_week(start_date: str, end_date: str) -> dict:
    """
    获取一周内所有有笔记的日期，返回 {date: [{name, text}]}
    """
    from datetime import date, timedelta
    from datetime import datetime

    result = {}
    start = datetime.fromisoformat(start_date).date()
    end   = datetime.fromisoformat(end_date).date()

    d = start
    while d <= end:
        date_str = d.isoformat()
        notes = fetch_notes_for_date(date_str)
        if notes:
            result[date_str] = notes
        d += timedelta(days=1)

    return result
