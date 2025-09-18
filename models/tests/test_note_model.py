from models.note import Note


def test_render_html_paragraphs_and_line_breaks():
    # Single newline becomes <br>, double newline creates paragraph break
    content = "Line1\nLine2\n\nPara2-Line1"
    n = Note(id="n1", title="t", content=content)
    if n.content_html != "<p>Line1<br>Line2</p><p>Para2-Line1</p>":
        raise AssertionError


def test_render_html_escapes_tags():
    # HTML should be escaped
    content = "<b>bold</b>\n<script>alert(1)</script>"
    n = Note(id="n2", title="t", content=content)
    if "&lt;b&gt;bold&lt;/b&gt;" not in n.content_html:
        raise AssertionError
    if "&lt;script&gt;alert(1)&lt;/script&gt;" not in n.content_html:
        raise AssertionError
    # Ensure raw tags do not appear
    if "<b>" in n.content_html:
        raise AssertionError
    if "<script>" in n.content_html:
        raise AssertionError


def test_update_content_syncs_html():
    n = Note(id="n3", title="t", content="first")
    if n.content_html != "<p>first</p>":
        raise AssertionError
    n.update_content("second\nline")
    if n.content_html != "<p>second<br>line</p>":
        raise AssertionError


def test_sync_html_method_recomputes_from_current_content():
    n = Note(id="n4", title="t", content="alpha")
    # Tamper content_html then sync and ensure recomputed from content
    n.content_html = "<p>TAMPERED</p>"
    n.sync_html()
    if n.content_html != "<p>alpha</p>":
        raise AssertionError


def test_from_dict_ignores_incoming_content_html():
    data = {
        "id": "n5",
        "title": "t",
        "content": "hello\nworld",
        "content_html": "<p>malicious override</p>",
        "tags": ["x"],
    }
    n = Note.from_dict(data)
    # from_dict should ignore incoming content_html and derive from content
    if n.content_html != "<p>hello<br>world</p>":
        raise AssertionError


def test_to_dict_contains_consistent_content_html():
    n = Note(id="n6", title="t", content="hello")
    d = n.to_dict()
    if d["content_html"] != "<p>hello</p>":
        raise AssertionError
    # After update, to_dict should reflect recomputed HTML
    n.update_content("hello\nthere")
    d2 = n.to_dict()
    if d2["content_html"] != "<p>hello<br>there</p>":
        raise AssertionError
