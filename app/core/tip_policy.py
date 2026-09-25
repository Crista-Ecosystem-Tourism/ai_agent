TIP_REPORT_REASONS = {"inaccurate", "unsafe", "spam", "copyright", "other"}
TIP_DAILY_SUBMISSION_LIMIT = 5
TIP_SUBMISSION_WINDOW_HOURS = 24
TIP_MAX_OPEN_DRAFTS = 10
TIP_DAILY_REPORT_LIMIT = 10


def clean_tip_body(value: str) -> str:
    body = " ".join(value.split())
    if len(body) < 10 or len(body) > 1200:
        raise ValueError("Заметка должна содержать от 10 до 1200 символов")
    return body


def clean_moderation_note(value: str | None) -> str | None:
    note = " ".join((value or "").split())
    if len(note) > 500:
        raise ValueError("Комментарий модератора не должен превышать 500 символов")
    return note or None
