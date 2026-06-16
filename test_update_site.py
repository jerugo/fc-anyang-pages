import unittest
from datetime import datetime, timedelta, timezone

import update_site


class NewsParsingTests(unittest.TestCase):
    def test_parse_fc_anyang_board_items_extracts_recent_rows(self):
        html = '''
        <table><tbody>
          <tr onclick="goDetail(1116)"><td>1029</td><td>FC안양, 안양천 플로깅 활동 진행&nbsp;</td><td>2026-05-20</td><td>1,296</td></tr>
          <tr onclick="goDetail(1115)"><td>1028</td><td>수비수 박종현, 조기 소집해제 이후 FC안양 복귀&nbsp;</td><td>2026-05-19</td><td>1,495</td></tr>
        </tbody></table>
        '''

        items = update_site.parse_fc_anyang_board_items(html, 'TNews', '구단소식')

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['title'], 'FC안양, 안양천 플로깅 활동 진행')
        self.assertEqual(items[0]['publishedAt'], '2026-05-20')
        self.assertEqual(items[0]['category'], 'event')
        self.assertEqual(items[0]['source'], 'official')
        self.assertIn('seq=1116', items[0]['url'])
        self.assertEqual(items[1]['category'], 'player')

    def test_parse_youtube_feed_items_extracts_recent_videos(self):
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
          <entry>
            <yt:videoId>abc123</yt:videoId>
            <title>⚽Goal of the Month</title>
            <published>2026-05-28T04:05:17+00:00</published>
          </entry>
        </feed>'''

        items = update_site.parse_youtube_feed_items(xml)

        self.assertEqual(items, [{
            'id': 'youtube-abc123',
            'source': 'youtube',
            'sourceLabel': 'YouTube',
            'title': '⚽Goal of the Month',
            'url': 'https://www.youtube.com/watch?v=abc123',
            'publishedAt': '2026-05-28',
            'category': 'sns',
        }])

    def test_parse_dcinside_rumor_items_filters_transfer_keywords(self):
        html = '''
        <tr class="ub-content us-post" data-no="601">
          <td class="gall_num">601</td><td class="gall_tit ub-word"><a href="/mgallery/board/view/?id=fcanyang2013&no=601">토마스 이적 썰</a><span class="reply_num">[3]</span></td>
          <td class="gall_writer">ㅇㅇ</td><td class="gall_date" title="2026-05-27 13:46:00">05.27</td><td class="gall_count">14</td><td class="gall_recommend">0</td>
        </tr>
        <tr class="ub-content us-post" data-no="602">
          <td class="gall_num">602</td><td class="gall_tit ub-word"><a href="/mgallery/board/view/?id=fcanyang2013&no=602">오늘 경기 어땠음?</a></td>
          <td class="gall_writer">ㅇㅇ</td><td class="gall_date">05.27</td><td class="gall_count">5</td><td class="gall_recommend">0</td>
        </tr>
        '''

        items = update_site.parse_dcinside_rumor_items(html, now_year=2026)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['source'], 'dcinside')
        self.assertEqual(items[0]['status'], 'unverified')
        self.assertEqual(items[0]['confidence'], 'low')
        self.assertIn('이적', items[0]['keywords'])
        self.assertEqual(items[0]['commentCount'], 3)
        self.assertIn('no=601', items[0]['url'])

    def test_parse_fmkorea_rumor_items_filters_transfer_keywords(self):
        html = '''
        <a href="/123456789">FC안양 외국인 공격수 영입 루머</a>
        <a href="/123456790">FC안양 오늘 경기 후기</a>
        '''

        items = update_site.parse_fmkorea_rumor_items(html)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['source'], 'fmkorea')
        self.assertEqual(items[0]['sourceLabel'], '에펨코리아')
        self.assertIn('영입', items[0]['keywords'])
        self.assertEqual(items[0]['status'], 'unverified')

    def test_parse_redflame_rumor_items_filters_keywords_and_dates(self):
        html = r'''
        \"href\":\"/post/4675?\" blah
        dangerouslySetInnerHTML\":{\"__html\":\"오늘 ㅆㅎㅈ에서 나온 루머\"}
        \"children\":37 \"children\":\"4일전\" \"children\":4 \"children\":4 \"children\":694
        \"href\":\"/post/4677?\" blah
        dangerouslySetInnerHTML\":{\"__html\":\"이번에 나온 카드케이스\"}
        \"children\":17 \"children\":\"1일전\" \"children\":0 \"children\":5 \"children\":220
        '''
        now = datetime(2026, 6, 1, tzinfo=timezone(timedelta(hours=9)))

        items = update_site.parse_redflame_rumor_items(html, now=now)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['source'], 'redflame')
        self.assertEqual(items[0]['sourceLabel'], 'REDFLAME')
        self.assertEqual(items[0]['title'], '오늘 ㅆㅎㅈ에서 나온 루머')
        self.assertEqual(items[0]['publishedAt'], '2026-05-28')
        self.assertEqual(items[0]['commentCount'], 4)
        self.assertEqual(items[0]['recommendCount'], 4)
        self.assertEqual(items[0]['viewCount'], 694)
        self.assertIn('ㅆㅎㅈ', items[0]['keywords'])
        self.assertEqual(items[0]['status'], 'unverified')

    def test_dedupe_items_prefers_first_seen_url(self):
        items = [
            {'title': 'A', 'url': 'https://example.com/1', 'publishedAt': '2026-05-28'},
            {'title': 'A copy', 'url': 'https://example.com/1', 'publishedAt': '2026-05-28'},
            {'title': 'B', 'url': 'https://example.com/2', 'publishedAt': '2026-05-27'},
        ]

        self.assertEqual(update_site.dedupe_items(items), [items[0], items[2]])

    def test_fetch_community_rumors_collects_all_sources_best_effort(self):
        now = datetime(2026, 6, 8, tzinfo=timezone(timedelta(hours=9)))
        old_datetime = update_site.datetime
        old_fetch_text = update_site.fetch_text

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now if tz else now.replace(tzinfo=None)

        dc_html = '''
        <tr class="ub-content us-post" data-no="701">
          <td class="gall_num">701</td><td class="gall_tit ub-word"><a href="/mgallery/board/view/?id=fcanyang2013&no=701">안양 영입 루머</a></td>
          <td class="gall_writer">ㅇㅇ</td><td class="gall_date" title="2026-06-08 13:46:00">06.08</td><td class="gall_count">14</td><td class="gall_recommend">1</td>
        </tr>
        '''
        fmkorea_html = '<a href="/123456789">FC안양 외국인 공격수 영입 루머</a>'
        redflame_html = r'''
        \"href\":\"/post/4675?\" blah
        dangerouslySetInnerHTML\":{\"__html\":\"오늘 ㅆㅎㅈ에서 나온 루머\"}
        \"children\":37 \"children\":\"0일전\" \"children\":4 \"children\":4 \"children\":694
        '''

        def fake_fetch_text(url, *args, **kwargs):
            if 'gall.dcinside.com' in url:
                return dc_html
            if 'fmkorea.com' in url:
                return fmkorea_html
            if 'redflame.co.kr' in url:
                return redflame_html
            return ''

        try:
            update_site.datetime = FixedDateTime
            update_site.fetch_text = fake_fetch_text
            items = update_site.fetch_community_rumors(days=7)
        finally:
            update_site.datetime = old_datetime
            update_site.fetch_text = old_fetch_text

        sources = {item['source'] for item in items}
        self.assertEqual(sources, {'dcinside', 'fmkorea', 'redflame'})
        self.assertTrue(all(item['status'] == 'unverified' for item in items))

    def test_fetch_community_rumors_does_not_use_stale_manual_fallback(self):
        old_manual = update_site.MANUAL_COMMUNITY_RUMORS
        old_fetch_text = update_site.fetch_text
        try:
            update_site.MANUAL_COMMUNITY_RUMORS = [{
                'id': 'manual-old',
                'source': 'fmkorea',
                'sourceLabel': '에펨코리아',
                'title': '안양 외국인 영입 루머',
                'url': 'https://example.com/rumor',
                'publishedAt': '2026-05-01',
                'keywords': ['영입', '루머'],
                'confidence': 'low',
                'status': 'unverified',
            }]
            update_site.fetch_text = lambda *args, **kwargs: ''
            items = update_site.fetch_community_rumors(days=7, fallback_days=30)
        finally:
            update_site.MANUAL_COMMUNITY_RUMORS = old_manual
            update_site.fetch_text = old_fetch_text

        self.assertEqual(items, [])


if __name__ == '__main__':
    unittest.main()
