import os
import tempfile
from flask import (
    Flask, Response, jsonify, request, render_template, send_file, url_for
)
from werkzeug.exceptions import RequestEntityTooLarge
from convert import convert_epub, s2t
from pathlib import Path

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


def parse_upload_limit():
    raw_value = os.getenv("MAX_UPLOAD_MIB", "4").strip()
    if not raw_value:
        return None

    try:
        limit_mib = float(raw_value)
    except ValueError as exc:
        raise RuntimeError("MAX_UPLOAD_MIB must be a number.") from exc

    if limit_mib <= 0:
        return None

    return int(limit_mib * 1024 * 1024)


app.config['MAX_CONTENT_LENGTH'] = parse_upload_limit()

def human_file_size(bytes_count):
    threshold = 1024
    units = ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
    if bytes_count < threshold:
        return f"{bytes_count} B"

    ui = -1
    while True:
        bytes_count /= threshold
        ui += 1
        if bytes_count < threshold or ui == (len(units) - 1):
            break

    return f"{round(bytes_count, 1)} {units[ui]}"


def upload_limit_label(limit):
    if limit is None:
        return "上傳大小：應用程式不設限"

    return f"檔案上限：{human_file_size(limit)}"


def public_base_url():
    configured_url = (
        os.getenv("PUBLIC_BASE_URL")
        or os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
    )
    if configured_url:
        if not configured_url.startswith(("http://", "https://")):
            configured_url = f"https://{configured_url}"
        return configured_url.rstrip("/")

    return request.url_root.rstrip("/")


def remove_file_safely(path):
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(_error):
    limit = app.config.get("MAX_CONTENT_LENGTH")
    return jsonify({
        "status": False,
        "error": f"檔案過大。{upload_limit_label(limit)}"
    }), 413

@app.route("/", methods=["GET"])
def render_index():
    limit = app.config.get("MAX_CONTENT_LENGTH")
    return render_template(
            "index.html.j2",
            canonical_url=f"{public_base_url()}/",
            limit=limit,
            limit_human_readable=upload_limit_label(limit),
            endpoint=url_for("upload_epub_sync")
        )


@app.route("/robots.txt")
def robots():
    return Response(
        f"User-agent: *\nAllow: /\nSitemap: {public_base_url()}/sitemap.xml\n",
        mimetype="text/plain"
    )


@app.route("/sitemap.xml")
def sitemap():
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{public_base_url()}/</loc></url>\n"
        '</urlset>\n',
        mimetype="application/xml"
    )

@app.route('/api/convert', methods=["POST"])
def upload_epub_sync():
    if 'upload' not in request.files:
        return jsonify({"status": False, "error": "尚未選擇檔案。"}), 400

    epub_file = request.files['upload']

    if epub_file.filename == '':
        return jsonify({"status": False, "error": "檔案沒有名稱。"}), 400

    limit = app.config.get("MAX_CONTENT_LENGTH")

    # Measure the uploaded file without relying on multipart content-length.
    epub_file.seek(0, 2)
    end_position = epub_file.tell()
    epub_file.seek(0)

    if limit is not None and end_position > limit:
        return jsonify({
            "status": False,
            "error": f"檔案過大。{upload_limit_label(limit)}"
        }), 413

    if epub_file and Path(epub_file.filename).suffix.lower() == ".epub":
        temp_file = tempfile.NamedTemporaryFile(suffix=".epub", delete=False)
        temp_file.close()
        try:
            convert_epub(epub_file, temp_file.name)
            print(f"Converted Successfully. File: {s2t(epub_file.filename)}")
            response = send_file(
                temp_file.name,
                as_attachment=True,
                download_name=s2t(epub_file.filename)
            )

            @response.call_on_close
            def cleanup_temp_file():
                remove_file_safely(temp_file.name)

            return response
        except Exception as e:
            remove_file_safely(temp_file.name)
            error_class = e.__class__.__name__
            return jsonify({"status": False, "error": f"轉換失敗（{error_class}）"}), 500
    else:
        return jsonify({"status": False, "error": "只接受 EPUB 格式的檔案。"}), 415 # Unsupported Media Type

if __name__ == "__main__":
    app.run(host="0.0.0.0")
