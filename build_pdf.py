"""Render MANUSCRIPT.md -> MANUSCRIPT.html -> MANUSCRIPT.pdf.
Markdown with tables + numbered footnote citations; figures inlined as base64 so the
PDF is self-contained. PDF is produced by headless Chrome (no LaTeX/pandoc needed)."""
import os, re, base64, subprocess, mimetypes
import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, 'MANUSCRIPT.md')
HTML = os.path.join(HERE, 'MANUSCRIPT.html')
PDF = os.path.join(HERE, 'MANUSCRIPT.pdf')
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def inline_images(html):
    def repl(m):
        src = m.group(1)
        path = src if os.path.isabs(src) else os.path.join(HERE, src)
        if not os.path.exists(path):
            return m.group(0)
        mime = mimetypes.guess_type(path)[0] or 'image/png'
        b64 = base64.b64encode(open(path, 'rb').read()).decode()
        return 'src="data:%s;base64,%s"' % (mime, b64)
    return re.sub(r'src="([^"]+)"', repl, html)

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Georgia","Times New Roman",serif; font-size: 10.2pt; line-height: 1.42;
       color: #111; max-width: 100%; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 6pt; }
h2 { font-size: 12.5pt; margin: 16pt 0 5pt; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
h3 { font-size: 10.8pt; margin: 11pt 0 3pt; }
p { margin: 0 0 6pt; text-align: justify; }
strong { font-weight: 700; }
code { font-family: "Menlo","Courier New",monospace; font-size: 8.6pt; background: #f4f4f4;
       padding: 0 2px; border-radius: 2px; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8.5pt;
        page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 3pt 5pt; text-align: left; vertical-align: top; }
th { background: #eee; font-weight: 700; }
td[align="right"], th[align="right"] { text-align: right; }
img { max-width: 100%; height: auto; display: block; margin: 8pt auto; page-break-inside: avoid; }
hr { border: none; border-top: 1px solid #ccc; margin: 14pt 0 6pt; }
sup { font-size: 0.75em; line-height: 0; }
a { color: #14375f; text-decoration: none; }
.footnote { font-size: 8.4pt; line-height: 1.32; }
.footnote ol { padding-left: 16pt; }
.footnote li { margin-bottom: 2.5pt; }
.footnote p { text-align: left; margin: 0; }
blockquote { color: #333; border-left: 3px solid #ccc; margin: 6pt 0; padding-left: 10pt; }
"""

def main():
    text = open(MD).read()
    html_body = markdown.markdown(
        text,
        extensions=['tables', 'footnotes', 'attr_list', 'sane_lists', 'md_in_html', 'fenced_code'],
        extension_configs={'footnotes': {'BACKLINK_TEXT': '&#8617;'}},
    )
    html_body = inline_images(html_body)
    doc = ("<!doctype html><html><head><meta charset='utf-8'>"
           "<title>Instrument reconciliation manuscript</title>"
           "<style>%s</style></head><body>%s</body></html>" % (CSS, html_body))
    open(HTML, 'w').write(doc)
    print("wrote", HTML, "(%d bytes)" % len(doc))

    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--print-to-pdf=%s" % PDF, "file://%s" % HTML],
                   check=True, capture_output=True)
    print("wrote", PDF, "(%d bytes)" % os.path.getsize(PDF))

if __name__ == "__main__":
    main()
