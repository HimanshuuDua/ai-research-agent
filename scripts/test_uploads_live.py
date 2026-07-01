"""Live upload test for TXT, DOCX, and PDF against production."""
import io
import json
import urllib.request
import uuid

BASE = "https://ai-research-agent-ecru-zeta.vercel.app"


def post_file(fname: str, content: bytes, ctype: str) -> dict:
    boundary = "----wb" + uuid.uuid4().hex
    body = b""
    body += ("--" + boundary + "\r\n").encode()
    body += ('Content-Disposition: form-data; name="file"; filename="' + fname + '"\r\n').encode()
    body += ("Content-Type: " + ctype + "\r\n\r\n").encode()
    body += content
    body += ("\r\n--" + boundary + "--\r\n").encode()
    req = urllib.request.Request(
        BASE + "/api/upload",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def make_pdf(text: str) -> bytes:
    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
    )
    stream = b"BT /F1 24 Tf 72 700 Td (" + text.encode() + b") Tj ET"
    objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n"
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\n"
    pdf += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    return pdf


def main() -> None:
    # TXT
    r = post_file("notes.txt", b"Quarterly revenue grew 25 percent in 2025.", "text/plain")
    print("TXT  ->", r.get("filename"), "| format:", r.get("format"), "| chars:", r.get("char_count"))

    # DOCX
    from docx import Document

    buf = io.BytesIO()
    doc = Document()
    doc.add_paragraph("Test DOCX: AI adoption increased in 2025.")
    doc.save(buf)
    r = post_file(
        "report.docx",
        buf.getvalue(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    print("DOCX ->", r.get("filename"), "| format:", r.get("format"), "| chars:", r.get("char_count"))

    # PDF
    r = post_file("doc.pdf", make_pdf("Hello PDF revenue grew 25 percent"), "application/pdf")
    print("PDF  ->", r.get("filename"), "| format:", r.get("format"), "| chars:", r.get("char_count"))
    print("PDF text sample:", (r.get("text") or "")[:60])


if __name__ == "__main__":
    main()
