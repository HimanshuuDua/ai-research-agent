from agent.context import set_active_documents
from agent.documents import extract_document
from agent.tools.document_reader import get_document_reader_tool


def test_extract_plain_text():
    data = b"Hello world\n\nSecond paragraph."
    doc = extract_document(data, "notes.txt")
    assert doc.text == "Hello world\n\nSecond paragraph."
    assert doc.format == "txt"
    assert not doc.truncated


def test_extract_json():
    data = b'{"title": "Report", "items": [1, 2]}'
    doc = extract_document(data, "data.json")
    assert "Report" in doc.text
    assert doc.format == "json"


def test_reject_legacy_doc():
    try:
        extract_document(b"fake", "report.doc")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert ".docx" in str(exc)


def test_read_document_lists_uploads():
    set_active_documents(
        [
            {
                "filename": "report.txt",
                "text": "Sample content",
                "char_count": 14,
                "format": "txt",
                "truncated": False,
            }
        ]
    )
    tool = get_document_reader_tool()
    listing = tool.func("")
    assert "report.txt" in listing

    content = tool.func("report.txt")
    assert "Sample content" in content
    set_active_documents(None)
