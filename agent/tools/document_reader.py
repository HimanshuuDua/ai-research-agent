from langchain_core.tools import Tool

from agent.context import get_active_documents

MAX_TOOL_OUTPUT_CHARS = 30_000


def _read_document(filename: str = "") -> str:
    if isinstance(filename, dict):
        filename = str(filename.get("filename", ""))
    filename = str(filename or "").strip()

    documents = get_active_documents() or []
    if not documents:
        return "No documents uploaded. Ask the user to upload a PDF, DOCX, or text file first."

    if not filename.strip():
        lines = ["Uploaded documents:"]
        for doc in documents:
            suffix = " (truncated)" if doc.get("truncated") else ""
            lines.append(
                f"- {doc['filename']} · {doc.get('format', 'text')} · "
                f"{doc.get('char_count', len(doc.get('text', '')))} chars{suffix}"
            )
        lines.append("Call read_document again with the filename to get the full text.")
        return "\n".join(lines)

    target = filename.strip().lower()
    match = next(
        (
            doc
            for doc in documents
            if doc["filename"].lower() == target or doc["filename"].lower().endswith(target)
        ),
        None,
    )
    if not match:
        available = ", ".join(doc["filename"] for doc in documents)
        return f"Document '{filename}' not found. Available: {available}"

    text = match.get("text", "")
    if len(text) > MAX_TOOL_OUTPUT_CHARS:
        return (
            f"Document: {match['filename']}\n\n"
            f"{text[:MAX_TOOL_OUTPUT_CHARS]}\n\n"
            "[Output truncated for tool limits. Summarize from this excerpt or ask for a section.]"
        )
    return f"Document: {match['filename']}\n\n{text}"


def get_document_reader_tool() -> Tool:
    return Tool(
        name="read_document",
        description=(
            "Read uploaded documents (PDF, DOCX, TXT, MD, CSV, JSON, HTML, RTF). "
            "Call with no filename to list uploads, or pass filename to read content. "
            "Use this when the user asks to summarize, analyze, or answer questions "
            "about an uploaded file."
        ),
        func=_read_document,
    )
