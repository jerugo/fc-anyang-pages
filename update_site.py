#!/usr/bin/env python3
import hashlib
import html as html_lib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote, urljoin

import requests

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

BASE = Path(__file__).resolve().parent
HTML_PATH = BASE / 'dist' / 'index.html'
POLICY_RULES_PATH = BASE / 'ticket_policy_rules.json'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json; charset=utf-8'}
TL_TEAM_URL = 'https://www.ticketlink.co.kr/sports/138/86'
FC_ANYANG_BASE_URL = 'https://www.fc-anyang.com'
NAVER_BLOG_RSS_URL = 'https://rss.blog.naver.com/fcanyang2013.xml'
YOUTUBE_RSS_URL = 'https://www.youtube.com/feeds/videos.xml?channel_id=UC9UFdmIfiMBKawVCAbRYy3g'
DCINSIDE_GALLERY_URL = 'https://gall.dcinside.com/mgallery/board/lists/?id=fcanyang2013'
FMKOREA_SEARCH_QUERIES = [
    '안양 영입', '안양 이적', '안양 임대', '안양 외국인', '안양 토마스',
    'FC안양 영입', 'FC안양 이적', 'FC안양 루머', 'FC안양 썰',
]
REDFLAME_BOARD_URL = 'https://www.redflame.co.kr/post'
TRANSFER_RUMOR_KEYWORDS = [
    '영입', '이적', '임대', '방출', '계약', '재계약', '오피셜', '썰', '루머',
    '온다', '나간다', '복귀', '콜업', '테스트', '외국인', '등록', '선수단',
    '토마스', '원두재', '마테우스', '유키치', '엘쿠라노', '아일톤', 'ㅆㅎㅈ', '썰호정',
    'FW', 'MF', 'DF', 'GK', '공격수', '미드필더', '수비수', '골키퍼', '용병',
]
MANUAL_COMMUNITY_RUMORS = [
    {
        'id': 'fmkorea-9927004518',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '(거피셜) 안양 승리의 토마스 기차 운행 중단',
        'summary': '토마스 이적설을 팬 커뮤니티에서 거피셜로 언급한 게시글.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&search_target=title_content&document_srl=9927004518&search_keyword=%EC%95%88%EC%96%91+%EC%9D%B4%EC%A0%81&page=1',
        'publishedAt': '2026-06-08',
        'keywords': ['토마스', '이적', '루머'],
        'commentCount': None,
        'viewCount': None,
        'recommendCount': None,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9925897585',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '안양 마테우스',
        'summary': '마테우스 관련 팬 커뮤니티 이적/외국인 선수 논의 글.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&search_target=title_content&document_srl=9925897585&search_keyword=%EC%95%88%EC%96%91+%EC%98%81%EC%9E%85&page=1',
        'publishedAt': '2026-06-08',
        'keywords': ['마테우스', '영입', '외국인'],
        'commentCount': None,
        'viewCount': None,
        'recommendCount': None,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9920077553',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '[단독]‘만능 멀티플레이어’ 토마스, 안양 떠나 울산 ‘전격’ 이적',
        'summary': '토마스 울산 이적 보도/커뮤니티 공유 글.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&search_target=title_content&document_srl=9920077553&search_keyword=%EC%95%88%EC%96%91+%EC%98%81%EC%9E%85&page=1',
        'publishedAt': '2026-06-06',
        'keywords': ['토마스', '울산', '이적'],
        'commentCount': None,
        'viewCount': None,
        'recommendCount': None,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9921007992',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '토마스는 그냥 안양의 복덩이였다',
        'summary': '토마스 관련 이적설 이후 팬 커뮤니티 반응 글.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&search_target=title_content&document_srl=9921007992&search_keyword=%EC%95%88%EC%96%91+%EC%9D%B4%EC%A0%81&page=1',
        'publishedAt': '2026-06-06',
        'keywords': ['토마스', '이적'],
        'commentCount': None,
        'viewCount': None,
        'recommendCount': None,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9881766039',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '안양/인천/광주',
        'summary': '주축 외국인 선수 2명은 6월 1주차 이후 윤곽 가능성. 국내 2팀/해외 1팀 관심, 영입은 당장 단계는 아니라는 루머.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&document_srl=9881766039',
        'publishedAt': '2026-05-28',
        'keywords': ['외국인', '이적', '영입', '루머'],
        'commentCount': 45,
        'viewCount': 20000,
        'recommendCount': 39,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9880392934',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '썰호정 단독| 울산은 토마스, 안양은 원두재 영입 추진중',
        'summary': '토마스 울산행 가능성과 안양의 원두재 영입 추진을 묶어 언급한 팬 커뮤니티 루머.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&document_srl=9880392934',
        'publishedAt': '2026-05-28',
        'keywords': ['토마스', '원두재', '영입', '이적'],
        'commentCount': 29,
        'viewCount': 30000,
        'recommendCount': 41,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9880457237',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '여러가지 루머',
        'summary': '울산이 토마스를 노리고, 안양의 원두재 건은 반반이라는 취지의 루머 정리글.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&document_srl=9880457237',
        'publishedAt': '2026-05-28',
        'keywords': ['토마스', '원두재', '루머'],
        'commentCount': 60,
        'viewCount': 30000,
        'recommendCount': 65,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9879336476',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '안양 빅네임',
        'summary': '원두재 영입 진행 중이고 분위기가 긍정적이라는 루머. 권경원 어필 언급.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&document_srl=9879336476',
        'publishedAt': '2026-05-27',
        'keywords': ['원두재', '영입', '루머'],
        'commentCount': 23,
        'viewCount': 20000,
        'recommendCount': 59,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9879391004',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '안양 울산 루머 정리해보면 (상상회로)',
        'summary': '토마스 매각 자금으로 원두재/재계약/보강을 상상해 본 팬 해석 글.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&document_srl=9879391004',
        'publishedAt': '2026-05-27',
        'keywords': ['토마스', '원두재', '이적', '재계약'],
        'commentCount': 13,
        'viewCount': 1113,
        'recommendCount': 5,
        'confidence': 'low',
        'status': 'unverified',
    },
    {
        'id': 'fmkorea-9857762996',
        'source': 'fmkorea',
        'sourceLabel': '에펨코리아',
        'title': '안양 외국인',
        'summary': '마테우스는 국내/해외 관심, 구단은 최우선 재계약 대상. 토마스는 해외 1팀 사전 문의와 국내 문의 정도라는 루머.',
        'url': 'https://www.fmkorea.com/index.php?mid=football_korean&document_srl=9857762996',
        'publishedAt': '2026-05-22',
        'keywords': ['마테우스', '토마스', '외국인', '재계약', '이적'],
        'commentCount': 36,
        'viewCount': 30000,
        'recommendCount': 71,
        'confidence': 'low',
        'status': 'unverified',
    },
]


def get_json(url, payload=None):
    if payload is None:
        r = requests.post(url, headers=HEADERS, timeout=30)
    else:
        r = requests.post(url, headers=HEADERS, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
    return r.json()


def strip_tags(s: str) -> str:
    text = re.sub(r'<.*?>', '', s)
    text = html_lib.unescape(text).replace('\xa0', ' ').replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', text).strip()


def normalize_date(value):
    if not value:
        return ''
    value = value.strip()
    for fmt in ('%Y-%m-%d', '%Y.%m.%d', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S+00:00'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
        except Exception:
            pass
    m = re.search(r'(20\d{2})[-.](\d{2})[-.](\d{2})', value)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return value[:10]


def classify_news_title(title):
    if re.search(r'영입|이적|임대|방출|계약|재계약|복귀|소집|선수|수비수|공격수|미드필더|골키퍼|GK|DF|MF|FW', title, re.I):
        return 'player'
    if re.search(r'이벤트|브랜드데이|모집|안내|클래스|행사|오픈|스탬프|팬|참가|데이|플로깅|캠페인|봉사', title):
        return 'event'
    if re.search(r'후원|협약|파트너|광고', title):
        return 'partner'
    return 'club'


def parse_int(value):
    text = str(value).replace(',', '').strip()
    if not text:
        return None
    m = re.match(r'([\d.]+)\s*만', text)
    if m:
        return int(float(m.group(1)) * 10000)
    try:
        return int(text)
    except Exception:
        return None


def normalize_short_date(value, now=None):
    now = now or datetime.now(timezone(timedelta(hours=9)))
    value = (value or '').strip()
    if re.match(r'\d{2}:\d{2}$', value):
        return now.strftime('%Y-%m-%d')
    if re.match(r'\d{2}\.\d{2}$', value):
        return f'{now.year}-{value[:2]}-{value[3:5]}'
    return normalize_date(value)


def dedupe_items(items):
    out = []
    seen = set()
    for item in items:
        key = item.get('id') or item.get('url') or f"{item.get('source')}::{item.get('title')}::{item.get('publishedAt')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def within_days(item, days=7, now=None):
    published = item.get('publishedAt')
    if not published:
        return True
    now = now or datetime.now(timezone(timedelta(hours=9)))
    try:
        dt = datetime.strptime(published[:10], '%Y-%m-%d').replace(tzinfo=now.tzinfo)
    except Exception:
        return True
    return dt.date() >= (now - timedelta(days=days)).date()


def parse_fc_anyang_board_items(page_html, menu, source_label):
    items = []
    for row_html in re.findall(r'(<tr[^>]*>.*?</tr>)', page_html, flags=re.S | re.I):
        if '202' not in row_html:
            continue
        date_m = re.search(r'(20\d{2}[-.]\d{2}[-.]\d{2})', row_html)
        if not date_m:
            continue
        seq_m = re.search(r'(?:seq=|goDetail\(|newsDetail\.asp\?menu=[^&]+&seq=)(\d+)', row_html)
        if not seq_m:
            continue
        seq = seq_m.group(1)
        link_texts = re.findall(r'<a[^>]*>(.*?)</a>', row_html, flags=re.S | re.I)
        title = ''
        for link_text in link_texts:
            candidate = strip_tags(link_text)
            if candidate and not candidate.isdigit():
                title = candidate
                break
        if not title:
            cells = [strip_tags(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, flags=re.S | re.I)]
            title = next((c for c in cells if c and not c.isdigit() and not re.match(r'20\d{2}[-.]\d{2}[-.]\d{2}', c) and not re.match(r'^[\d,]+$', c)), '')
        if not title:
            continue
        items.append({
            'id': f'{menu}-{seq}',
            'source': 'official',
            'sourceLabel': source_label,
            'title': title,
            'url': f'{FC_ANYANG_BASE_URL}/news/newsDetail.asp?menu={menu}&seq={seq}',
            'publishedAt': normalize_date(date_m.group(1)),
            'category': classify_news_title(title),
        })
    return items


def parse_naver_blog_rss_items(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return items
    channel = root.find('channel')
    if channel is None:
        return items
    for item in channel.findall('item'):
        title = item.findtext('title') or ''
        link = item.findtext('link') or ''
        pub_date = item.findtext('pubDate') or ''
        published = ''
        try:
            from email.utils import parsedate_to_datetime
            published = parsedate_to_datetime(pub_date).astimezone(timezone(timedelta(hours=9))).strftime('%Y-%m-%d')
        except Exception:
            published = normalize_date(pub_date)
        title = strip_tags(title)
        if not title:
            continue
        items.append({
            'id': f"naver-{hashlib.sha1((link or title).encode('utf-8')).hexdigest()[:12]}",
            'source': 'naver_blog',
            'sourceLabel': '네이버 블로그',
            'title': title,
            'url': link,
            'publishedAt': published,
            'category': classify_news_title(title),
        })
    return items


def parse_youtube_feed_items(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return items
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    for entry in root.findall('atom:entry', ns):
        video_id = entry.findtext('yt:videoId', default='', namespaces=ns)
        title = entry.findtext('atom:title', default='', namespaces=ns).strip()
        published = normalize_date(entry.findtext('atom:published', default='', namespaces=ns))
        if not video_id or not title:
            continue
        items.append({
            'id': f'youtube-{video_id}',
            'source': 'youtube',
            'sourceLabel': 'YouTube',
            'title': title,
            'url': f'https://www.youtube.com/watch?v={video_id}',
            'publishedAt': published,
            'category': 'sns',
        })
    return items


def parse_dcinside_rumor_items(page_html, now_year=None):
    now_year = now_year or datetime.now(timezone(timedelta(hours=9))).year
    items = []
    for row in re.findall(r'<tr[^>]+ub-content[^>]*>(.*?)</tr>', page_html, flags=re.S | re.I):
        no_m = re.search(r'data-no="(\d+)"', row) or re.search(r'<td[^>]+gall_num[^>]*>\s*(\d+)', row, flags=re.S | re.I)
        link_m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', row, flags=re.S | re.I)
        if not no_m or not link_m:
            continue
        title = strip_tags(link_m.group(2))
        keywords = [kw for kw in TRANSFER_RUMOR_KEYWORDS if kw.lower() in title.lower()]
        if not keywords:
            continue
        date_title_m = re.search(r'class="gall_date"[^>]*title="([^"]+)"', row, flags=re.S | re.I)
        if date_title_m:
            published = normalize_date(date_title_m.group(1))
        else:
            date_text_m = re.search(r'class="gall_date"[^>]*>(.*?)</td>', row, flags=re.S | re.I)
            date_text = strip_tags(date_text_m.group(1)) if date_text_m else ''
            if re.match(r'\d{2}\.\d{2}', date_text):
                published = f'{now_year}-{date_text[:2]}-{date_text[3:5]}'
            else:
                published = normalize_date(date_text)
        reply_m = re.search(r'class="reply_num"[^>]*>\s*\[(\d+)\]', row, flags=re.S | re.I)
        cells = [strip_tags(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S | re.I)]
        view_count = parse_int(cells[-2]) if len(cells) >= 2 else None
        recommend_count = parse_int(cells[-1]) if len(cells) >= 1 else None
        url = urljoin('https://gall.dcinside.com', html_lib.unescape(link_m.group(1)))
        items.append({
            'id': f'dcinside-{no_m.group(1)}',
            'source': 'dcinside',
            'sourceLabel': '디시인사이드',
            'title': title,
            'url': url,
            'publishedAt': published,
            'keywords': keywords,
            'commentCount': int(reply_m.group(1)) if reply_m else 0,
            'viewCount': view_count,
            'recommendCount': recommend_count,
            'confidence': 'low',
            'status': 'unverified',
        })
    return items


def parse_fmkorea_rumor_items(page_html, now=None):
    now = now or datetime.now(timezone(timedelta(hours=9)))
    items = []
    seen = set()

    row_pattern = r'<tr[^>]*>\s*<td[^>]*>.*?</tr>'
    for row in re.findall(row_pattern, page_html, flags=re.S | re.I):
        href_m = re.search(r'<a[^>]+href="([^"]*(?:document_srl=\d+|/\d{6,})[^"]*)"[^>]*>(.*?)</a>', row, flags=re.S | re.I)
        if not href_m:
            continue
        cells = [strip_tags(c) for c in re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S | re.I)]
        if len(cells) < 5:
            continue
        title = strip_tags(href_m.group(2))
        if not title or ('FC안양' not in title and 'fc안양' not in title.lower() and '안양' not in title):
            continue
        keywords = [kw for kw in TRANSFER_RUMOR_KEYWORDS if kw.lower() in title.lower()]
        if not keywords:
            continue
        url = urljoin('https://www.fmkorea.com', html_lib.unescape(href_m.group(1)))
        if url in seen:
            continue
        seen.add(url)
        doc_m = re.search(r'(?:document_srl=|/)(\d{6,})', url)
        items.append({
            'id': f"fmkorea-{doc_m.group(1) if doc_m else hashlib.sha1(url.encode('utf-8')).hexdigest()[:10]}",
            'source': 'fmkorea',
            'sourceLabel': '에펨코리아',
            'title': title,
            'url': url,
            'publishedAt': normalize_short_date(cells[-3] if len(cells) >= 3 else '', now=now),
            'keywords': keywords,
            'commentCount': parse_int(comment_m.group(1)) if (comment_m := re.search(r'\b(\d+)\s*$', title)) else None,
            'viewCount': parse_int(cells[-2]) if len(cells) >= 2 else None,
            'recommendCount': parse_int(cells[-1]) if len(cells) >= 1 else None,
            'confidence': 'low',
            'status': 'unverified',
        })

    if items:
        return items

    # Fallback for alternate/listless markup: keep URL/title even when date columns are unavailable.
    for href, raw_title in re.findall(r'<a[^>]+href="([^"]*(?:document_srl=\d+|/\d{6,})[^"]*)"[^>]*>(.*?)</a>', page_html, flags=re.S | re.I):
        title = strip_tags(raw_title)
        if not title or ('FC안양' not in title and 'fc안양' not in title.lower() and '안양' not in title):
            continue
        keywords = [kw for kw in TRANSFER_RUMOR_KEYWORDS if kw.lower() in title.lower()]
        if not keywords:
            continue
        url = urljoin('https://www.fmkorea.com', html_lib.unescape(href))
        if url in seen:
            continue
        seen.add(url)
        doc_m = re.search(r'(?:document_srl=|/)(\d{6,})', url)
        items.append({
            'id': f"fmkorea-{doc_m.group(1) if doc_m else hashlib.sha1(url.encode('utf-8')).hexdigest()[:10]}",
            'source': 'fmkorea',
            'sourceLabel': '에펨코리아',
            'title': title,
            'url': url,
            'publishedAt': '',
            'keywords': keywords,
            'commentCount': None,
            'viewCount': None,
            'recommendCount': None,
            'confidence': 'low',
            'status': 'unverified',
        })
    return items


def parse_redflame_date(date_text, now=None):
    now = now or datetime.now(timezone(timedelta(hours=9)))
    date_text = (date_text or '').strip()
    rel_m = re.match(r'(\d+)일전', date_text)
    if rel_m:
        return (now - timedelta(days=int(rel_m.group(1)))).strftime('%Y-%m-%d')
    m = re.match(r'(\d{2})\.(\d{2})\.(\d{2})', date_text)
    if m:
        return f'20{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return normalize_date(date_text)


def parse_redflame_rumor_items(page_html, now=None):
    """Parse FC Anyang fan-site REDFLAME board cards from Next.js/RSC HTML."""
    normalized = page_html.replace('\\"', '"').replace('\\u0026', '&')
    starts = list(re.finditer(r'"href":"/post/(\d+)\?"', normalized))
    items = []
    for idx, match in enumerate(starts):
        post_id = match.group(1)
        end = starts[idx + 1].start() if idx + 1 < len(starts) else match.start() + 6000
        segment = normalized[match.start():end]
        title_m = re.search(r'dangerouslySetInnerHTML":\{"__html":"([^"]*)"', segment)
        if not title_m:
            continue
        title = strip_tags(title_m.group(1))
        keywords = [kw for kw in TRANSFER_RUMOR_KEYWORDS if kw.lower() in title.lower()]
        if not keywords:
            continue
        date_m = re.search(r'"children":"(\d+일전|\d{2}\.\d{2}\.\d{2})"', segment)
        numbers = [int(n) for n in re.findall(r'"children":(\d+)', segment)]
        items.append({
            'id': f'redflame-{post_id}',
            'source': 'redflame',
            'sourceLabel': 'REDFLAME',
            'title': title,
            'url': f'https://www.redflame.co.kr/post/{post_id}',
            'publishedAt': parse_redflame_date(date_m.group(1), now=now) if date_m else '',
            'keywords': keywords,
            'commentCount': numbers[-3] if len(numbers) >= 3 else None,
            'recommendCount': numbers[-2] if len(numbers) >= 2 else None,
            'viewCount': numbers[-1] if numbers else None,
            'confidence': 'low',
            'status': 'unverified',
        })
    return items


def fetch_text_with_curl(url, headers=None):
    cmd = [
        'curl', '-fsSL', '--http1.1', '--tlsv1.2', '--ciphers', 'DEFAULT@SECLEVEL=1',
        '-A', (headers or {}).get('User-Agent', 'Mozilla/5.0'),
    ]
    for key, value in (headers or {}).items():
        if key.lower() != 'user-agent':
            cmd.extend(['-H', f'{key}: {value}'])
    cmd.append(url)
    result = subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    for enc in ('utf-8', 'cp949', 'euc-kr'):
        try:
            return result.stdout.decode(enc)
        except UnicodeDecodeError:
            pass
    return result.stdout.decode('utf-8', errors='replace')


def fetch_text(url, headers=None):
    try:
        r = requests.get(url, headers=headers or {'User-Agent': 'Mozilla/5.0'}, timeout=30)
        r.raise_for_status()
        if r.encoding is None or r.encoding.lower() in ('iso-8859-1', 'latin-1'):
            r.encoding = r.apparent_encoding or 'utf-8'
        return r.text
    except requests.exceptions.SSLError:
        return fetch_text_with_curl(url, headers=headers)


def fetch_recent_news(days=7):
    items = []
    sources = [
        (f'{FC_ANYANG_BASE_URL}/news/news.asp?menu=TNews', 'TNews', '구단소식'),
        (f'{FC_ANYANG_BASE_URL}/news/news.asp?menu=TNotice', 'TNotice', '공지사항'),
    ]
    for url, menu, label in sources:
        try:
            items.extend(parse_fc_anyang_board_items(fetch_text(url), menu, label))
        except Exception as e:
            print(f'[news] FC안양 {label} 수집 오류: {e}')
    try:
        items.extend(parse_naver_blog_rss_items(fetch_text(NAVER_BLOG_RSS_URL)))
    except Exception as e:
        print(f'[news] 네이버 블로그 RSS 수집 오류: {e}')
    try:
        items.extend(parse_youtube_feed_items(fetch_text(YOUTUBE_RSS_URL)))
    except Exception as e:
        print(f'[news] YouTube RSS 수집 오류: {e}')
    items = [item for item in dedupe_items(items) if within_days(item, days=days)]
    items.sort(key=lambda x: (x.get('publishedAt') or '', x.get('source') or ''), reverse=True)
    return items[:12]


def fetch_community_rumors(days=7, fallback_days=10):
    items = list(MANUAL_COMMUNITY_RUMORS)
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://gall.dcinside.com/'}
    urls = [DCINSIDE_GALLERY_URL]
    for keyword in TRANSFER_RUMOR_KEYWORDS[:15]:
        urls.append(f'{DCINSIDE_GALLERY_URL}&s_type=search_subject_memo&s_keyword={quote(keyword)}')
    for url in urls:
        try:
            items.extend(parse_dcinside_rumor_items(fetch_text(url, headers=headers)))
        except Exception as e:
            print(f'[rumor] 디시인사이드 수집 오류: {e}')
    fmkorea_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36',
        'Referer': 'https://www.fmkorea.com/',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    }
    for query in FMKOREA_SEARCH_QUERIES:
        url = f'https://www.fmkorea.com/search.php?mid=football_korean&search_target=title_content&search_keyword={quote(query)}'
        try:
            items.extend(parse_fmkorea_rumor_items(fetch_text(url, headers=fmkorea_headers)))
        except Exception as e:
            print(f'[rumor] 에펨코리아 수집 오류({query}): {e}')
    try:
        redflame_headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.redflame.co.kr/'}
        items.extend(parse_redflame_rumor_items(fetch_text(REDFLAME_BOARD_URL, headers=redflame_headers)))
    except Exception as e:
        print(f'[rumor] REDFLAME 수집 오류: {e}')
    deduped = dedupe_items(items)
    recent_items = [item for item in deduped if within_days(item, days=days)]
    if recent_items:
        items = recent_items
    else:
        # Some community sites (notably FMKorea) intermittently return 430/rate-limit
        # responses to scheduled crawlers. Do not let the dashboard section disappear
        # completely when the fresh scrape is blocked; fall back to the latest
        # already-collected/community-board items for a wider window.
        items = [item for item in deduped if within_days(item, days=fallback_days)]
        if items:
            print(f'[rumor] 최근 {days}일 내 항목 없음: 최근 {fallback_days}일 백업 항목 {len(items)}개 사용')
    items.sort(key=lambda x: (x.get('publishedAt') or '', x.get('recommendCount') or 0, x.get('commentCount') or 0, x.get('viewCount') or 0), reverse=True)
    return items[:10]


def extract(text: str, a: str, b: str) -> str:
    m = re.search(a + '(.*?)' + b, text, re.S)
    return m.group(1) if m else ''


def fetch_ranking():
    obj = get_json('https://www.kleague.com/record/teamRank.do?leagueId=1&year=2026&stadium=all&recordType=rank')
    rows = []
    for item in obj['data']['teamRank']:
        rows.append({
            'rank': item['rank'],
            'club': item['teamName'],
            'games': item['gameCount'],
            'points': item['gainPoint'],
            'win': item['winCnt'],
            'draw': item['tieCnt'],
            'loss': item['lossCnt'],
            'goals': item['gainGoal'],
            'against': item['lossGoal'],
            'diff': item['gapCnt'],
        })
    return rows


def fetch_league_schedule(year, team_id=None):
    all_rows = []
    for month in range(1, 13):
        payload = {'leagueId': 1, 'year': str(year), 'month': f'{month:02d}', 'ticketYn': ''}
        if team_id:
            payload['teamId'] = team_id
        obj = get_json('https://www.kleague.com/getScheduleList.do', payload)
        for item in obj['data']['scheduleList']:
            all_rows.append(item)

    deduped = []
    seen = set()
    for item in all_rows:
        key = (item.get('year'), item.get('roundId'), item.get('gameId'), item.get('homeTeam'), item.get('awayTeam'))
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    deduped.sort(key=lambda x: (x.get('gameDate', ''), x.get('gameTime', ''), x.get('gameId') or 0))
    return deduped


def fetch_schedule():
    all_rows = []
    for item in fetch_league_schedule(2026, team_id='K27'):
        status = '종료' if item.get('gameStatus') == 'FE' or item.get('endYn') == 'Y' else '예정'
        all_rows.append({
            'date': item['gameDate'],
            'time': item['gameTime'],
            'home': item['homeTeamName'],
            'away': item['awayTeamName'],
            'homeGoal': item.get('homeGoal'),
            'awayGoal': item.get('awayGoal'),
            'status': status,
            'venue': item['fieldName'],
            'venueFull': item.get('fieldNameFull') or item['fieldName'],
            'round': item['roundId'],
            'ticketProvider': item.get('company'),
            'ticketStatus': item.get('ticketStatus'),
            'ticketYn': item.get('ticketYn'),
            'goodsCode': item.get('goodsCode'),
            'externalUrl': item.get('externalUrl'),
            'ticketOpenDate': None,
            'ticketOpenDateSource': None,
        })
    all_rows.sort(key=lambda x: (x['date'], x['time']))
    return all_rows


def fetch_round_progress(year):
    """라운드 종료 시점별 FC안양 순위/승점/승무패 추이를 계산합니다."""
    matches = [
        item for item in fetch_league_schedule(year)
        if (item.get('gameStatus') == 'FE' or item.get('endYn') == 'Y') and item.get('meetSeq') == 1
    ]
    teams = {}
    for item in matches:
        teams[item['homeTeam']] = item['homeTeamName']
        teams[item['awayTeam']] = item['awayTeamName']

    table = {
        team_id: {'teamId': team_id, 'club': club, 'points': 0, 'win': 0, 'draw': 0, 'loss': 0, 'goals': 0, 'against': 0, 'diff': 0, 'games': 0}
        for team_id, club in teams.items()
    }

    progress = []
    split_top_ids = None
    rounds = sorted({int(item['roundId']) for item in matches if item.get('roundId') is not None})
    for round_id in rounds:
        round_matches = [item for item in matches if int(item['roundId']) == round_id]
        # 완전히 끝난 라운드만 순위 추이에 반영
        if len(round_matches) < max(1, len(teams) // 2):
            continue

        for item in sorted(round_matches, key=lambda x: (x.get('gameDate', ''), x.get('gameTime', ''), x.get('gameId') or 0)):
            home = table[item['homeTeam']]
            away = table[item['awayTeam']]
            home_goal = int(item.get('homeGoal') or 0)
            away_goal = int(item.get('awayGoal') or 0)

            home['games'] += 1
            away['games'] += 1
            home['goals'] += home_goal
            home['against'] += away_goal
            away['goals'] += away_goal
            away['against'] += home_goal
            home['diff'] = home['goals'] - home['against']
            away['diff'] = away['goals'] - away['against']

            if home_goal > away_goal:
                home['win'] += 1
                home['points'] += 3
                away['loss'] += 1
            elif home_goal < away_goal:
                away['win'] += 1
                away['points'] += 3
                home['loss'] += 1
            else:
                home['draw'] += 1
                away['draw'] += 1
                home['points'] += 1
                away['points'] += 1

        base_ranked = sorted(
            table.values(),
            key=lambda r: (-r['points'], -r['diff'], -r['goals'], -r['win'], r['club'])
        )

        # K리그는 33R 이후 파이널A/B 그룹 순위가 고정되어 서로 순위를 넘지 않습니다.
        if round_id == 33 and len(base_ranked) >= 12:
            split_top_ids = {row['teamId'] for row in base_ranked[:6]}

        if split_top_ids and round_id >= 34:
            top_group = [row for row in base_ranked if row['teamId'] in split_top_ids]
            bottom_group = [row for row in base_ranked if row['teamId'] not in split_top_ids]
            ranked = top_group + bottom_group
        else:
            ranked = base_ranked

        for idx, row in enumerate(ranked, start=1):
            row['rank'] = idx

        anyang = next((row for row in ranked if row['club'] == '안양'), None)
        if anyang:
            progress.append({
                'year': year,
                'round': round_id,
                'rank': anyang['rank'],
                'points': anyang['points'],
                'win': anyang['win'],
                'draw': anyang['draw'],
                'loss': anyang['loss'],
                'games': anyang['games'],
            })

    return progress


def load_ticket_policy_rules():
    if not POLICY_RULES_PATH.exists():
        return {}
    try:
        data = json.loads(POLICY_RULES_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def apply_policy_open_date(match, policy_rules):
    if match.get('status') == '종료':
        return None

    home_team = match.get('home')
    if not home_team:
        return None

    rule = policy_rules.get(home_team)
    if not isinstance(rule, dict):
        return None

    match_dt = None
    try:
        match_dt = datetime.strptime(match['date'], '%Y.%m.%d')
    except Exception:
        return None

    # 1) 고정 D-n 규칙
    general = rule.get('general_sale')
    if isinstance(general, dict):
        try:
            days_before = int(general.get('days_before'))
            open_time = str(general.get('time', '14:00'))
            open_date = (match_dt - timedelta(days=days_before)).strftime('%Y-%m-%d')
            return f'{open_date} {open_time}'
        except Exception:
            pass

    # 2) 요일 기반 규칙 (예: 제주)
    weekday_rule = rule.get('general_sale_weekday_rule')
    if isinstance(weekday_rule, dict):
        try:
            open_time = str(weekday_rule.get('time', '12:00'))
            weekday = match_dt.weekday()  # Mon=0 ... Sun=6

            # 주말 경기(금/토/일) -> 해당 주 월요일 정오
            if weekday in (4, 5, 6) and weekday_rule.get('weekend_match_open_day') == 'monday':
                open_dt = match_dt - timedelta(days=weekday)
                return f"{open_dt.strftime('%Y-%m-%d')} {open_time}"
        except Exception:
            pass

    return None


def fetch_ticket_schedule():
    """
    Ticketlink 화면 캡처(OCR) 기반으로 예매 오픈일을 추출합니다.
    - 데스크톱 페이지 진입
    - '홈경기만 보기' 체크 해제 상태로 전환
    - 페이지 캡처(artifact) + OCR 텍스트에서 '오픈예정' 패턴 파싱

    Returns:
        dict: key = 'DT::YYYY.MM.DD HH:MM'
              value = {ticketOpenDate}
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('[ticket] playwright 미설치 - 티켓 스크래핑 건너뜀')
        return {}

    result = {}
    artifact_dir = BASE / 'artifacts'
    artifact_dir.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ko-KR',
                viewport={'width': 1440, 'height': 2200},
            )
            page = context.new_page()

            page.goto('https://www.ticketlink.co.kr/sports/138/86', timeout=45000, wait_until='domcontentloaded')
            page.wait_for_timeout(5000)

            # 체크박스가 체크되어 있으면 반드시 해제
            try:
                cb = page.locator('input[type="checkbox"]').first
                if cb.count() and cb.is_checked():
                    cb.click(force=True)
                    page.wait_for_timeout(2000)
            except Exception:
                try:
                    toggle = page.get_by_text('홈경기만 보기').first
                    if toggle.count():
                        toggle.click(force=True)
                        page.wait_for_timeout(2000)
                except Exception:
                    pass

            # 3) 캡처 저장 (디버깅/검증용)
            shot_path = artifact_dir / 'ticketlink_schedule_full.png'
            try:
                page.screenshot(path=str(shot_path), full_page=True)
                print(f'[ticket] screenshot saved: {shot_path}')
            except Exception as e:
                print(f'[ticket] screenshot failed: {e}')

            # 4) OCR 기반 오픈예정 파싱
            if pytesseract and Image and shot_path.exists():
                try:
                    ocr_text = pytesseract.image_to_string(Image.open(shot_path), lang='kor+eng')
                except Exception:
                    ocr_text = ''

                # 블록 단위로 '경기일시 ... 오픈예정일시' 패턴 추출
                # 예: 2026.04.22(수) 19:30 ... 2026.04.17(금) 14:00 오픈예정
                block_pattern = re.compile(
                    r'(20\d{2}\.\d{2}\.\d{2})\([^)]+\)\s*(\d{2}:\d{2})[\s\S]{0,120}?(20\d{2}\.\d{2}\.\d{2})\([^)]+\)\s*(\d{2}:\d{2})\s*오픈예정'
                )
                hits = 0
                for m in block_pattern.finditer(ocr_text):
                    game_date = m.group(1)
                    game_time = m.group(2)
                    open_date = m.group(3)
                    open_time = m.group(4)
                    open_iso = f"{open_date.replace('.', '-')} {open_time}"
                    result[f'DT::{game_date} {game_time}'] = {
                        'ticketOpenDate': open_iso,
                    }
                    hits += 1

                # 오픈예정일시만 단독 인식된 경우(보조)
                if hits == 0:
                    only_open = re.findall(r'(20\d{2}\.\d{2}\.\d{2})\([^)]+\)\s*(\d{2}:\d{2})\s*오픈예정', ocr_text)
                    if only_open:
                        print(f'[ticket] OCR open-only lines: {len(only_open)} (match-date 미포함)')

            browser.close()

    except Exception as e:
        print(f'[ticket] 스크래핑 오류: {e}')

    print(f'[ticket] 수집된 티켓 키 수: {len(result)}')
    return result


def fetch_ticketlink_open_date_by_goods_code(goods_code):
    """Ticketlink mapi/sports/schedule 에서 goodsCode 기준 오픈일을 조회합니다."""
    if not goods_code:
        return None

    url = f'https://mapi.ticketlink.co.kr/mapi/sports/schedule?scheduleId={goods_code}'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://www.ticketlink.co.kr',
        'Referer': 'https://www.ticketlink.co.kr/',
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        obj = r.json()
        data = obj.get('data') if isinstance(obj, dict) else None
        reserve_open_date = data.get('reserveOpenDate') if isinstance(data, dict) else None
        if reserve_open_date is None:
            return None
        ts = int(reserve_open_date) / 1000
        kst = timezone(timedelta(hours=9))
        return datetime.fromtimestamp(ts, tz=kst).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return None


def merge_ticket_data(schedule, ticket_map, policy_rules):
    """
    1) OCR 직접 추출값을 우선 반영
    2) Ticketlink goodsCode 기반 오픈일 API 조회
    3) 그 외 홈팀 정책 룰(공식 예매 오픈 규칙)로 보완
    """
    goods_open_cache = {}

    for match in schedule:
        match['ticketOpenDate'] = None
        match['ticketOpenDateSource'] = None

        if match.get('status') == '종료':
            continue

        # OCR 일치키 우선
        dt_key = f"DT::{match['date']} {match['time']}"
        ticket_hit = ticket_map.get(dt_key)
        if ticket_hit and ticket_hit.get('ticketOpenDate'):
            match['ticketOpenDate'] = ticket_hit['ticketOpenDate']
            match['ticketOpenDateSource'] = 'screenshot_ocr'
            continue

        # goodsCode가 있으면 Ticketlink API에서 직접 오픈일 조회
        goods_code = match.get('goodsCode')
        if goods_code:
            if goods_code not in goods_open_cache:
                goods_open_cache[goods_code] = fetch_ticketlink_open_date_by_goods_code(goods_code)
            goods_open = goods_open_cache.get(goods_code)
            if goods_open:
                match['ticketOpenDate'] = goods_open
                match['ticketOpenDateSource'] = 'ticketlink_api'
                continue

        # 정책 룰 기반 추정값은 표시하지 않음: 직접 확인된 OCR/API 값만 반영

    return schedule


def fetch_player_ids():
    players = []
    for page in [1, 2, 3]:
        html = requests.get(
            f'https://www.kleague.com/player.do?type=active&leagueId=1&teamId=K27&page={page}',
            headers={'User-Agent': 'Mozilla/5.0'}, timeout=30
        ).text
        cards = re.findall(r'onPlayerClicked\((\d+)\)(.*?)</div>\s*</div>\s*</div>', html, re.S)
        for pid, block in cards:
            name_m = re.search(r'<span class="name">([^<]+)<span class="small">안양</span></span>', block, re.S)
            no_m = re.search(r'<span class="num campton">No\.(\d+)</span>', block, re.S)
            if name_m and no_m:
                players.append((pid, name_m.group(1).strip(), int(no_m.group(1))))
    uniq = {}
    for pid, name, no in players:
        uniq[pid] = (name, no)
    return [(pid, name, no) for pid, (name, no) in uniq.items()]


def parse_player_detail(pid, fallback_name, fallback_no):
    html = requests.get(
        f'https://www.kleague.com/record/playerDetail.do?playerId={pid}',
        headers={'User-Agent': 'Mozilla/5.0'}, timeout=30
    ).text

    info_block = extract(html, r'<h3 class="tit-box style2">선수 정보</h3>.*?<table class="style2 center">', r'</table>')
    cells = [strip_tags(x) for x in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', info_block, re.S)]
    info = {}
    for i in range(0, len(cells) - 1, 2):
        if cells[i]:
            info[cells[i]] = cells[i + 1]

    pos = info.get('포지션', '')
    stat2, stat3 = ('실점', '클린시트') if pos == 'GK' else ('득점', '도움')

    season_block = extract(html, r'<h3 class="tit-box style2">시즌별</h3>.*?<tbody>', r'</tbody>')
    rows = []
    for row_html in re.findall(r'<tr>(.*?)</tr>', season_block, re.S):
        vals = [strip_tags(x) for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.S)]
        if vals:
            rows.append(vals)
    row2026 = next((r for r in rows if r and r[0] == '2026'), None)
    total = next((r for r in rows if r and r[0] == '합계'), None)

    def parse(r):
        if not r:
            return None
        r = r + [''] * (20 - len(r))
        return {
            'league_apps': r[2],
            'league_stat2': r[3],
            'league_stat3': r[4],
            'career_apps': r[17],
            'career_stat2': r[18],
            'career_stat3': r[19],
        }

    cur = parse(row2026) or {'league_apps': '-', 'league_stat2': '-', 'league_stat3': '-', 'career_apps': '-', 'career_stat2': '-', 'career_stat3': '-'}
    tot = parse(total) or cur

    return {
        'no': int(info.get('배번', fallback_no)),
        'name': info.get('이름', fallback_name),
        'pos': pos,
        'birth': info.get('생년월일', ''),
        'nation': info.get('국적', ''),
        's2026': f"{cur['league_apps']} / {cur['league_stat2']} / {cur['league_stat3']}",
        'career': f"{tot['career_apps']} / {tot['career_stat2']} / {tot['career_stat3']}",
    }


def fetch_players():
    out = []
    for pid, name, no in fetch_player_ids():
        try:
            out.append(parse_player_detail(pid, name, no))
        except Exception:
            out.append({'no': no, 'name': name, 'pos': '', 'birth': '', 'nation': '', 's2026': '- / - / -', 'career': '- / - / -'})
    out.sort(key=lambda x: x['no'])
    return out


def replace_const_json(text, const_name, data):
    replacement = f"const {const_name} = {json.dumps(data, ensure_ascii=False, indent=6)};"
    pattern = rf'const {const_name} = (?:\{{.*?\}}|\[(?:.*?)\]);'
    return re.sub(pattern, lambda m: replacement, text, flags=re.S)


def replace_const_array(text, const_name, data):
    return replace_const_json(text, const_name, data)


def main():
    ranking = fetch_ranking()
    schedule = fetch_schedule()
    ticket_map = fetch_ticket_schedule()
    policy_rules = load_ticket_policy_rules()
    schedule = merge_ticket_data(schedule, ticket_map, policy_rules)
    round_progress = {
        '2025': fetch_round_progress(2025),
        '2026': fetch_round_progress(2026),
    }
    players = fetch_players()
    recent_news = fetch_recent_news(days=7)
    community_rumors = fetch_community_rumors(days=7)

    text = HTML_PATH.read_text(encoding='utf-8')
    text = replace_const_array(text, 'ranking', ranking)
    text = replace_const_array(text, 'schedule', schedule)
    text = replace_const_json(text, 'roundProgress', round_progress)
    text = replace_const_array(text, 'players', players)
    text = replace_const_array(text, 'recentNews', recent_news)
    text = replace_const_array(text, 'communityRumors', community_rumors)
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).strftime('%Y-%m-%d %H:%M KST')
    text = re.sub(r'(<span id="updateDateText">)(.*?)(</span>)', lambda m: f'{m.group(1)}{today}{m.group(3)}', text)
    HTML_PATH.write_text(text, encoding='utf-8')

    ticket_open = sum(1 for m in schedule if m.get('ticketOpenDate'))
    ticket_on_sale = sum(1 for m in schedule if m.get('goodsCode'))
    print(json.dumps({
        'updated': str(HTML_PATH),
        'date': today,
        'ranking_rows': len(ranking),
        'schedule_rows': len(schedule),
        'player_rows': len(players),
        'recent_news_rows': len(recent_news),
        'community_rumor_rows': len(community_rumors),
        'round_progress_years': {year: len(rows) for year, rows in round_progress.items()},
        'ticket_on_sale': ticket_on_sale,
        'ticket_open_date_known': ticket_open,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
