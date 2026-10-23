import gui_tools
from controller import ActionController
from eye_interface import MockBackend, MockEye


def test_verify_text_marks_screen_content_as_untrusted():
    eye = MockEye()
    gui_tools.init(eye, ActionController(eye, MockBackend(eye)))

    result = gui_tools.verify_text.invoke({"text": "Mock Search"})

    assert result.startswith("<screen_data>\n")
    assert result.endswith("\n</screen_data>")
    assert '"matches": ["Mock Search"]' in result
