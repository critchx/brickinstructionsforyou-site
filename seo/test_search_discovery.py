import datetime
import unittest
import xml.etree.ElementTree as ET
from search_discovery import PageMeta, eligible, sitemap_urls, build_feed, page_path, BASE

URL = BASE + '/lego-instructions/75495-star-wars-stormtrooper-concept-art-helmet/'

class SearchDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.meta = PageMeta()
        self.meta.feed(f'''<html><head><title>LEGO 75495 — instructions coming soon</title>
        <meta name="description" content="Building instructions for LEGO 75495 are coming soon.">
        <link rel="canonical" href="{URL}"></head></html>''')

    def test_page_can_be_indexed(self):
        self.assertTrue(eligible(self.meta, URL))
        self.assertEqual(page_path(URL), 'public/lego-instructions/75495-star-wars-stormtrooper-concept-art-helmet/index.html')

    def test_noindex_is_excluded(self):
        self.meta.feed('<meta name="robots" content="noindex,follow">')
        self.assertFalse(eligible(self.meta, URL))

    def test_wrong_canonical_is_excluded(self):
        self.assertFalse(eligible(self.meta, BASE + '/lego-instructions/some-other-set/'))

    def test_sitemap_filters_other_hosts(self):
        xml = f'''<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>{URL}</loc><lastmod>2026-11-13</lastmod></url>
        <url><loc>https://other.example/lego-instructions/bad/</loc><lastmod>2026-11-14</lastmod></url>
        </urlset>'''
        self.assertEqual(sitemap_urls(xml), {URL: '2026-11-13'})

    def test_rss_feed_is_valid_and_accurate(self):
        feed = build_feed([(URL, '2026-11-13', self.meta)])
        root = ET.fromstring(feed)
        self.assertEqual(root.findtext('channel/item/link'), URL)
        self.assertIn('coming soon', root.findtext('channel/item/description'))
        self.assertEqual(root.find('channel/{http://www.w3.org/2005/Atom}link').get('rel'), 'self')

if __name__ == '__main__':
    unittest.main()
