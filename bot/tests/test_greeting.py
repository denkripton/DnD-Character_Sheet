from app.utils.greeting import FALLBACK_NAME, greeting_text


def test_greeting_uses_name():
    text = greeting_text("hero")
    assert "hero" in text


def test_greeting_uses_first_name_when_no_username():
    text = greeting_text("Hana")
    assert "Hana" in text


def test_greeting_fallback_name():
    assert FALLBACK_NAME in greeting_text(None)