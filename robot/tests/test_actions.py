import actions as actions_module
from actions import GEMINI_TIMEOUT_MS, RobotActions


class FakeHardware:
    pass


def make_actions_without_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    return RobotActions(FakeHardware())


def test_vision_question_with_front_word_never_moves(monkeypatch):
    actions = make_actions_without_gemini(monkeypatch)
    decision = actions._fallback_decide("앞에 뭐가 보여")
    assert decision["steps"][0]["action"] == "VISION_QUESTION"


def test_describe_camera_view_is_vision_question(monkeypatch):
    actions = make_actions_without_gemini(monkeypatch)
    decision = actions._fallback_decide("카메라에 보이는 것을 모두 말해 봐")
    assert decision["steps"][0]["action"] == "VISION_QUESTION"


def test_explicit_forward_command_still_moves(monkeypatch):
    actions = make_actions_without_gemini(monkeypatch)
    decision = actions._fallback_decide("앞으로 한 번 가")
    assert decision["steps"][0]["action"] == "MOVE_FORWARD"


def test_gemini_client_has_request_timeout(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(actions_module.genai, "Client", fake_client)

    RobotActions(FakeHardware())

    assert captured["http_options"].timeout == GEMINI_TIMEOUT_MS
