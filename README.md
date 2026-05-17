# epub_convert

`epub_convert` converts Simplified Chinese EPUB files to Traditional Chinese EPUB files.

The project includes:

- a command-line converter for one or more `.epub` files
- a Flask web app for drag-and-drop upload and download
- deployment entrypoints for `gunicorn` and `mod_wsgi`

## What It Does

The converter opens the EPUB archive, rewrites text-based content with OpenCC, and builds a new EPUB output.

- Uses OpenCC with the `s2tw.json` preset
- Converts content inside `.htm`, `.html`, `.xhtml`, `.ncx`, and `.opf` files
- Preserves other files in the EPUB archive as-is
- Renames archive paths and output filenames with the same Simplified-to-Traditional conversion
- Updates OPF language metadata from `zh-CN` to `zh-TW`
- Detects common encodings from BOM, XML declarations, and HTML meta tags

## Requirements

- Python 3.6+

## Install

```bash
pip install -r requirements.txt
```

Main Python dependencies:

- `flask`
- `opencc`
- `gunicorn`

## CLI Usage

Convert one file:

```bash
python convert.py book.epub
```

Convert multiple files:

```bash
python convert.py book1.epub book2.epub
```

Convert a glob pattern:

```bash
python convert.py "*.epub"
```

Output behavior:

- If the converted filename changes after Simplified-to-Traditional conversion, that converted name is used.
- If the filename does not change, the output file gets a `-tc.epub` suffix.

## Run The Web App

Start the local development server:

```bash
python web.py
```

Then open `http://127.0.0.1:5000`.

Web app behavior:

- Accepts a single `.epub` upload
- Has no app-level upload limit by default
- Returns the converted EPUB directly as a download

Optional upload limit:

- Set `MAX_UPLOAD_MIB` to a positive number to restore an app-level limit
- Leave `MAX_UPLOAD_MIB` unset, `0`, or a negative value for no app-level limit

## API

The web app exposes one conversion endpoint:

- `POST /api/convert`

Form field:

- `upload`: EPUB file

Success response:

- Binary EPUB download

Error responses:

- `400` when no file is provided
- `413` when the file is too large
- `415` when the upload is not an EPUB file
- `500` when conversion fails

## Deployment

### Gunicorn

The repository includes a `Procfile` with:

```bash
gunicorn web:app --timeout 60
```

If you are deploying behind Apache, Nginx, a CDN, or a hosting platform, those layers can still impose their own body-size or timeout limits even when the Flask app does not.

### Apache `mod_wsgi`

The repository also includes `web.wsgi`:

```python
from web import app as application
```

Example virtual host:

```apache
<VirtualHost *:80>
    ServerName domain.name

    WSGIDaemonProcess appname user=user1 group=group1 threads=5
    WSGIScriptAlias / /location/to/folder/web.wsgi
    Alias /static /location/to/folder/static

    <Directory "/location/to/folder">
        Require all granted
    </Directory>
</VirtualHost>
```

## Project Files

- [`convert.py`](convert.py) - core EPUB conversion logic and CLI
- [`web.py`](web.py) - Flask app and upload endpoint
- [`templates/index.html.j2`](templates/index.html.j2) - web UI template
- [`static/upload.js`](static/upload.js) - client-side upload flow
- [`static/main.css`](static/main.css) - UI styling

## License

MIT. See [`LICENSE`](LICENSE).
