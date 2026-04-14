#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

BASE = Path(__file__).resolve().parent
HTML_PATH = BASE / 'dist' / 'index.html'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json; charset=utf-8'}
TL_TEAM_URL = 'https://www.ticketlink.co.kr/sports/138/86'


def get_json(url, payload=None):
    if payload is None:
        r = requests.post(url, headers=HEADERS, timeout=30)
    else:
        r = requests.post(url, headers=HEADERS, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
    return r.json()


def strip_tags(s: str) -> str:
    return re.sub(r'<.*?>', '', s).replace('&nbsp;', ' ').strip()


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


def fetch_schedule():
    all_rows = []
    for month in range(1, 13):
        payload = {'leagueId': 1, 'teamId': 'K27', 'year': '2026', 'month': f'{month:02d}', 'ticketYn': ''}
        obj = get_json('https://www.kleague.com/getScheduleList.do', payload)
        for item in obj['data']['scheduleList']:
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
    deduped = []
    seen = set()
    for row in all_rows:
        key = (row['date'], row['time'], row['home'], row['away'])
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    deduped.sort(key=lambda x: (x['date'], x['time']))
    return deduped


def fetch_ticket_schedule():
    """
    Ticketlink 화면 캡처 기반으로 예매 오픈일을 추출합니다.
    - 데스크톱 페이지 진입
    - '홈경기만 보기' 체크 해제 상태로 전환
    - 페이지 캡처(artifact) + OCR 텍스트에서 '오픈예정' 패턴 파싱
    - mapi 응답 캡처가 가능하면 우선 사용

    Returns:
        dict: key = 'YYYY.MM.DD HH:MM home away' 또는 'DATE::YYYY.MM.DD'
              value = {ticketOpenDate, scheduleId, available}
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('[ticket] playwright 미설치 - 티켓 스크래핑 건너뜀')
        return {}

    result = {}
    artifact_dir = BASE / 'artifacts'
    artifact_dir.mkdir(parents=True, exist_ok=True)

    def upsert_date_key(game_date: str, open_date_iso: str):
        if not game_date or not open_date_iso:
            return
        result[f'DATE::{game_date}'] = {
            'ticketOpenDate': open_date_iso,
            'scheduleId': None,
            'available': False,
        }

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

            # 1) API 응답 캡처 (가능하면 가장 신뢰)
            def handle_response(response):
                if 'mapi.ticketlink.co.kr/mapi/sports/schedules' not in response.url:
                    return
                try:
                    data = response.json()
                    items = data.get('data')
                    if not isinstance(items, list):
                        return
                    kst = timezone(timedelta(hours=9))
                    for item in items:
                        game_date = item.get('gameDate', '')
                        game_time = item.get('gameTime', '')
                        home = item.get('homeTeamName', '')
                        away = item.get('awayTeamName', '')
                        schedule_id = item.get('scheduleId') or item.get('goodsCode')
                        sale_start_ts = item.get('saleStartDatetime') or item.get('saleStart')

                        open_date = None
                        if sale_start_ts:
                            try:
                                ts = int(str(sale_start_ts)) // 1000
                                open_date = datetime.fromtimestamp(ts, tz=kst).strftime('%Y-%m-%d %H:%M')
                            except Exception:
                                pass

                        key = f'{game_date} {game_time} {home} {away}'
                        result[key] = {
                            'ticketOpenDate': open_date,
                            'scheduleId': str(schedule_id) if schedule_id else None,
                            'available': bool(schedule_id),
                        }
                        if open_date and game_date:
                            upsert_date_key(game_date, open_date)
                except Exception:
                    pass

            page.on('response', handle_response)

            # 2) 화면 진입 + 홈경기만 보기 체크 해제
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
                    open_date = m.group(3)
                    open_time = m.group(4)
                    open_iso = f"{open_date.replace('.', '-')} {open_time}"
                    upsert_date_key(game_date, open_iso)
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


def merge_ticket_data(schedule, ticket_map):
    """
    티켓링크 스크래핑 결과를 K리그 일정 데이터에 병합합니다.
    K리그 API의 goodsCode → 직접 예매 링크 생성.
    Playwright 스크래핑으로 ticketOpenDate 보완.

    FC안양 홈경기(티켓링크) 중 오픈일 미확정 건은
    공식 게시 패턴 기반 일반예매 D-4 14:00(KST)로 보수적 추정치를 채웁니다.
    """
    kst = timezone(timedelta(hours=9))

    for match in schedule:
        match['ticketOpenDateSource'] = None

        # K리그 API goodsCode로 직접 예매 URL 구성 (이미 오픈)
        if match.get('goodsCode'):
            match['ticketOpenDate'] = None
            continue

        # Playwright 스크래핑 데이터 매핑 (정확키 우선, 날짜키 보조)
        key = f"{match['date']} {match['time']} {match['home']} {match['away']}"
        date_key = f"DATE::{match['date']}"

        ticket_hit = ticket_map.get(key) or ticket_map.get(date_key)
        if ticket_hit:
            match['ticketOpenDate'] = ticket_hit.get('ticketOpenDate')
            if match['ticketOpenDate']:
                if key in ticket_map:
                    match['ticketOpenDateSource'] = 'ticketlink'
                else:
                    match['ticketOpenDateSource'] = 'screenshot_ocr'
            if ticket_hit.get('scheduleId') and not match.get('goodsCode'):
                match['goodsCode'] = ticket_hit['scheduleId']
                match['ticketOpenDate'] = None
                match['ticketOpenDateSource'] = None
            continue

        # fallback: 티켓링크 + 예정 경기는 D-4 14:00 추정(홈/원정 공통)
        is_ticketlink = match.get('ticketProvider') == 'T'
        is_upcoming = match.get('status') != '종료'
        if is_ticketlink and is_upcoming:
            try:
                game_dt = datetime.strptime(match['date'], '%Y.%m.%d').replace(tzinfo=kst)
                open_dt = (game_dt - timedelta(days=4)).replace(hour=14, minute=0)
                match['ticketOpenDate'] = open_dt.strftime('%Y-%m-%d %H:%M')
                match['ticketOpenDateSource'] = 'policy_d4'
            except Exception:
                match['ticketOpenDate'] = None
                match['ticketOpenDateSource'] = None
        else:
            match['ticketOpenDate'] = None
            match['ticketOpenDateSource'] = None

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


def replace_const_array(text, const_name, data):
    replacement = f"const {const_name} = {json.dumps(data, ensure_ascii=False, indent=6)};"
    pattern = rf'const {const_name} = \[(?:.*?)\];'
    return re.sub(pattern, lambda m: replacement, text, flags=re.S)


def main():
    ranking = fetch_ranking()
    schedule = fetch_schedule()
    ticket_map = fetch_ticket_schedule()
    schedule = merge_ticket_data(schedule, ticket_map)
    players = fetch_players()

    text = HTML_PATH.read_text(encoding='utf-8')
    text = replace_const_array(text, 'ranking', ranking)
    text = replace_const_array(text, 'schedule', schedule)
    text = replace_const_array(text, 'players', players)
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
        'ticket_on_sale': ticket_on_sale,
        'ticket_open_date_known': ticket_open,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
