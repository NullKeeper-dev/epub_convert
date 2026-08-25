import codecs
import re
import zipfile
import opencc
from pathlib import Path

# only initailize OpenCC once, or it would be very slow
converter = opencc.OpenCC("s2tw")
XML_ENCODING_RE = re.compile(br'^\s*<\?xml[^>]*encoding=["\']([A-Za-z0-9._-]+)["\']', re.IGNORECASE)
HTML_CHARSET_RE = re.compile(br'<meta[^>]+charset=["\']?\s*([A-Za-z0-9._-]+)', re.IGNORECASE)
HTML_CONTENT_TYPE_RE = re.compile(br'<meta[^>]+content=["\'][^"\']*charset=([A-Za-z0-9._-]+)', re.IGNORECASE)
# ponytail: regex covers ordinary EPUB CSS; use a CSS parser if nested/custom syntax appears.
FONT_FACE_RE = re.compile(r"@font-face\s*\{[^{}]*\}", re.IGNORECASE | re.DOTALL)
FONT_DECLARATION_RE = re.compile(
    r"(^|[;{])\s*font(?:-family)?\s*:[^;}]*;?",
    re.IGNORECASE | re.MULTILINE
)
TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
STYLE_ATTRIBUTE_RE = re.compile(
    r"(\bstyle\s*=\s*)([\"'])(.*?)\2",
    re.IGNORECASE | re.DOTALL
)
FONT_ATTRIBUTE_RE = re.compile(
    r"\s+(?:face|font-family)\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)",
    re.IGNORECASE
)

def convert_epub(epub, output=None, convert_all=False):
    target_filetype = ["htm", "html", "xhtml", "ncx", "opf"]

    origin = zipfile.ZipFile(epub, mode="r")
    copy = zipfile.ZipFile(output, mode="w")

    for i, fn in enumerate(origin.namelist()):
        info = origin.getinfo(fn)
        extension = Path(fn).suffix[1:] # remove heading `.`
        if extension in target_filetype or (convert_all and extension in ["css", "svg"]):
            # if file extension is targeted file type
            sc_content = origin.read(fn)
            tc_content = convert_content(sc_content, reset_fonts=convert_all)
            if extension == "opf":
                tc_content = tc_content.replace(b"<dc:language>zh-CN</dc:language>", b"<dc:language>zh-TW</dc:language>")
            copy.writestr(s2t(fn), tc_content, compress_type=info.compress_type)
        else:
            # write other files directly
            copy.writestr(s2t(fn), origin.read(fn), compress_type=info.compress_type)

    origin.close()
    copy.close()
    return output

def convert_content(content, reset_fonts=False):
    if isinstance(content, str):
        converted = s2t(content)
        return remove_custom_fonts(converted) if reset_fonts else converted

    encoding = detect_encoding(content)
    text = content.decode(encoding)
    converted = s2t(text)
    if reset_fonts:
        converted = remove_custom_fonts(converted)
    return converted.encode(encoding)

def remove_custom_fonts(content):
    content = FONT_FACE_RE.sub("", content)
    content = FONT_DECLARATION_RE.sub(lambda match: match.group(1), content)

    def clean_tag(match):
        tag = STYLE_ATTRIBUTE_RE.sub(
            lambda style: (
                style.group(1)
                + style.group(2)
                + FONT_DECLARATION_RE.sub(
                    lambda declaration: declaration.group(1),
                    style.group(3)
                )
                + style.group(2)
            ),
            match.group(0)
        )
        return FONT_ATTRIBUTE_RE.sub("", tag)

    return TAG_RE.sub(clean_tag, content)

def detect_encoding(content):
    for bom, encoding in (
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
    ):
        if content.startswith(bom):
            return encoding

    head = content[:1024]
    for pattern in (XML_ENCODING_RE, HTML_CHARSET_RE, HTML_CONTENT_TYPE_RE):
        match = pattern.search(head)
        if match:
            return match.group(1).decode("ascii")

    return "utf-8"

def s2t(text):
    return converter.convert(text)

if __name__ == "__main__":
    import argparse
    import glob
    import time
    from io import BytesIO

    parser = argparse.ArgumentParser(description="Convert simplified chinese to traditional chinese in epub.")
    parser.add_argument('file', nargs='+', help="epub files")
    parser.add_argument(
        '--convert-all',
        action='store_true',
        help="experimental: remove custom fonts so all text uses the reader default"
    )
    args = parser.parse_args()

    if len(args.file) == 1 and "*" in args.file[0]:
        fn_list = glob.glob(args.file[0])
    else:
        fn_list = args.file

    for fn in fn_list:
        path = Path(fn)
        directory = path.parent.absolute()
        filename = path.name

        if not path.suffix == ".epub":
            print(f"Skipping file {fn}, which is not an epub document.")
            continue
        elif filename == s2t(filename):
            output_fn = fn[:-5] + '-tc.epub'
        else:
            output_fn = s2t(filename)

        t = time.time()
        print(f"Converting {fn}")
        buffer = BytesIO()
        output = convert_epub(fn, buffer, convert_all=args.convert_all)
        with open(Path.joinpath(directory, output_fn), "wb") as f:
            f.write(buffer.getvalue())
        print(f"File {fn} is successfully converted. Time elapsed: {round(time.time() - t, 2)}s")
