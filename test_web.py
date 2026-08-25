import unittest
import zipfile
from io import BytesIO

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


if __name__ == "__main__":
    unittest.main()
