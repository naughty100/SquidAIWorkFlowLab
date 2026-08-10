from ai_workflow_lab.cli import console_safe_text


def test_console_safe_text_escapes_unicode_for_legacy_windows_consoles() -> None:
    rendered = console_safe_text('{"title":"研究∙提案"}')

    assert rendered == '{"title":"\\u7814\\u7a76\\u2219\\u63d0\\u6848"}'
    rendered.encode("gbk")
