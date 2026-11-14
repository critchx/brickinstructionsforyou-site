from datetime import date
import re
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from latest_published import homepage_candidates, inspect_published, rewrite, BASE

CARD = '''<a class="set-card" href="/lego-instructions/{slug}/"><span class="badge-new">NEW</span><div class="set-info"><div class="set-number">{number}</div><div class="set-name">{name}</div><div class="set-meta">Icons • 2026</div></div></a>'''

def home():
    cards = [CARD.format(slug=f"{i}-test", number=i, name=f"Model {i}") for i in range(1, 8)]
    return ('<html><div class="grid"><a href="/other/">OTHER</a></div>'
            '<h2>Latest 2026 LEGO instructions</h2><p>Fresh guides</p><div class="grid">' + '\n'.join(cards) + '</div><footer></footer></html>')

def page(i, release="1 November 2026", noindex=False, has_video=True):
    return ('<html><head><link rel="canonical" href="' + BASE + f'/lego-instructions/{i}-test/">' +
            ('<meta name="robots" content="noindex">' if noindex else '') + '</head><body>' +
            (f'<p>Released on {release}.</p>' if release else '') +
            ('<script type="application/ld+json">{"@type":"VideoObject"}</script>' if has_video else '') +
            '</body></html>')

def latest():
    return ('<html><head><title>Latest 2027 LEGO Instructions</title>'
            '<meta name="description" content="2027 video guides">'
            '<meta property="og:title" content="Latest 2027 LEGO Instructions">'
            '<meta property="og:description" content="2027 videos">'
            '<meta name="twitter:title" content="Latest 2027 LEGO Instructions">'
            '<meta name="twitter:description" content="2027 videos">'
            '<link rel="canonical" href="' + BASE + '/latest/"></head>'
            '<header>LATEST 2027 VIDEOS</header>'
            '<main id="pageContent"><h1>Latest LEGO Instructions</h1><div class="grid">OLD</div></main><footer>Keep</footer></html>')

class TestLatestPublished(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 11, 14)
        self.pages = {f"/lego-instructions/{i}-test/": page(i) for i in range(1, 8)}

    def test_selects_correct_homepage_grid(self):
        year, cards = homepage_candidates(home(), self.today)
        self.assertEqual(year, 2026)
        self.assertEqual(len(cards), 7)
        self.assertEqual(cards[0][2], '1 Model 1')
        self.assertNotIn('/other/', cards[0][0])

    def test_rewrites_latest_with_video_guides_and_links(self):
        out, report = rewrite(home(), latest(), self.pages, self.today)
        self.assertEqual(report['recently_released'], 7)
        self.assertNotIn('LATEST 2027 VIDEOS', out)
        self.assertIn('Latest LEGO Building Instructions', out)
        self.assertIn('/lego-instructions/1-test/', out)
        self.assertIn('id="latestPublishedItemList"', out)
        self.assertIn('<footer>Keep</footer>', out)
        self.assertIn('Recently released LEGO sets', out)

    def test_skips_nonindexable_and_missing_video(self):
        self.pages['/lego-instructions/1-test/'] = page(1, noindex=True)
        self.pages['/lego-instructions/2-test/'] = page(2, has_video=False)
        out, report = rewrite(home(), latest(), self.pages, self.today)
        self.assertEqual(len(report['skipped']), 2)
        self.assertNotIn('href="/lego-instructions/1-test/"', out)
        self.assertNotIn('href="/lego-instructions/2-test/"', out)

    def test_future_releases_not_in_released_section(self):
        self.pages['/lego-instructions/1-test/'] = page(1, release="1 January 2027")
        out, report = rewrite(home(), latest(), self.pages, self.today)
        self.assertEqual(report['recently_released'], 6)
        self.assertIn('Newest instruction videos', out)

    def test_canonical_mismatch_rejected(self):
        self.assertEqual(inspect_published(BASE+'/lego-instructions/1-test/', page(2), self.today), (False, None))

    def test_idempotent(self):
        out, _ = rewrite(home(), latest(), self.pages, self.today)
        second, _ = rewrite(home(), out, self.pages, self.today)
        self.assertEqual(out, second)

    def test_refuses_tiny_homepage_section(self):
        with self.assertRaises(ValueError):
            homepage_candidates('<h2>Latest 2026 LEGO instructions</h2><div class="grid"></div>', self.today)

if __name__ == '__main__':
    unittest.main()
