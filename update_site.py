#!/usr/bin/env python3
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
HTML_PATH = BASE / 'dist' / 'index.html'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json; charset=utf-8'}


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
    players = fetch_players()

    text = HTML_PATH.read_text(encoding='utf-8')
    text = replace_const_array(text, 'ranking', ranking)
    text = replace_const_array(text, 'schedule', schedule)
    text = replace_const_array(text, 'players', players)
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).strftime('%Y-%m-%d %H:%M KST')
    text = re.sub(r'(<span id="updateDateText">)(.*?)(</span>)', lambda m: f'{m.group(1)}{today}{m.group(3)}', text)
    HTML_PATH.write_text(text, encoding='utf-8')

    print(json.dumps({
        'updated': str(HTML_PATH),
        'date': today,
        'ranking_rows': len(ranking),
        'schedule_rows': len(schedule),
        'player_rows': len(players)
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
