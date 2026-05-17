import unittest

from scripts.render_report import render_html


class RenderReportTests(unittest.TestCase):
    def test_render_html_rejects_unsafe_article_url(self):
        html = render_html(
            [
                {
                    "rank": 1,
                    "score": 10,
                    "category": "AI",
                    "source_type": "news",
                    "title_en": "Title",
                    "title_zh": "标题",
                    "summary_en": "Summary",
                    "summary_zh": "摘要",
                    "source_name": "Source",
                    "url": 'javascript:alert(1)" onclick="alert(2)',
                }
            ]
        )

        self.assertIn('href="#"', html)
        self.assertNotIn("javascript:alert", html)
        self.assertNotIn("onclick=", html)

    def test_render_html_escapes_http_url_attribute(self):
        html = render_html(
            [
                {
                    "rank": 1,
                    "score": 10,
                    "category": "AI",
                    "source_type": "news",
                    "title_en": "Title",
                    "title_zh": "标题",
                    "summary_en": "Summary",
                    "summary_zh": "摘要",
                    "source_name": "Source",
                    "url": 'https://example.com/?a=1&b="x"',
                }
            ]
        )

        self.assertIn('href="https://example.com/?a=1&amp;b=&quot;x&quot;"', html)


if __name__ == "__main__":
    unittest.main()
