# FC Anyang Pages

FC안양 일정, 순위, 선수기록을 한눈에 보는 Cloudflare Pages 사이트.

## Files
- dist/index.html: 배포되는 정적 페이지
- update_site.py: K리그 데이터를 수집해 HTML 내 데이터를 갱신하는 스크립트
- package.json: 보조 실행 스크립트

## Update
```bash
python3 update_site.py
wrangler pages deploy dist --project-name fc-anyang-hub
```
