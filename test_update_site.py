import unittest

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

    def test_dedupe_items_prefers_first_seen_url(self):
        items = [
            {'title': 'A', 'url': 'https://example.com/1', 'publishedAt': '2026-05-28'},
            {'title': 'A copy', 'url': 'https://example.com/1', 'publishedAt': '2026-05-28'},
            {'title': 'B', 'url': 'https://example.com/2', 'publishedAt': '2026-05-27'},
        ]

        self.assertEqual(update_site.dedupe_items(items), [items[0], items[2]])


if __name__ == '__main__':
    unittest.main()
