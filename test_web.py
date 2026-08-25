import unittest
import zipfile
from io import BytesIO

from convert import convert_epub
from web import app


class WebMetadataTest(unittest.TestCase):
    def test_indexing_metadata_and_upload_limit(self):
        client = app.test_client()

        page = client.get("/")
        self.assertIn('lang="zh-Hant-TW"', page.get_data(as_text=True))
        self.assertIn("檔案上限：4.0 MiB", page.get_data(as_text=True))
        self.assertIn("Sitemap:", client.get("/robots.txt").get_data(as_text=True))
        self.assertIn("<urlset", client.get("/sitemap.xml").get_data(as_text=True))

        source = BytesIO()
        with zipfile.ZipFile(source, "w") as epub:
            epub.writestr("chapter.xhtml", "<p>简体中文电子书</p>")
        source.seek(0)

        converted = client.post(
            "/api/convert",
            data={"upload": (source, "简体.epub")},
            content_type="multipart/form-data"
        )
        self.assertEqual(converted.status_code, 200)
        converted_data = converted.get_data()
        converted.close()
        with zipfile.ZipFile(BytesIO(converted_data)) as epub:
            self.assertIn("簡體中文電子書", epub.read("chapter.xhtml").decode())

    def test_convert_all_removes_custom_fonts_only(self):
        source = BytesIO()
        with zipfile.ZipFile(source, "w") as epub:
            epub.writestr(
                "styles.css",
                '@font-face { font-family: Fancy; src: url(fancy.otf); }\n'
                'body { font-family: Fancy; font-weight: bold; color: red; }'
            )
            epub.writestr(
                "chapter.xhtml",
                '<p style="font: 1em Fancy; color: red">简体文字</p>'
                '<font face="Fancy">共同文字</font>'
            )
        source.seek(0)
        output = BytesIO()

        convert_epub(source, output, convert_all=True)

        with zipfile.ZipFile(output) as epub:
            css = epub.read("styles.css").decode()
            chapter = epub.read("chapter.xhtml").decode()
        self.assertNotIn("Fancy", css + chapter)
        self.assertNotIn("@font-face", css)
        self.assertIn("font-weight: bold", css)
        self.assertIn("color: red", css + chapter)
        self.assertIn("簡體文字", chapter)


if __name__ == "__main__":
    unittest.main()
