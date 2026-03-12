"""Tests for MessageProcessor._extract_questions static method."""
import pytest
from app.core.services.processor import MessageProcessor


class TestExtractQuestions:
    """Test extraction of [Q]-tagged questions from AI response text."""

    def test_no_questions(self):
        text = "Вот несколько отличных мест для вас.\nРекомендую посетить парк."
        clean, questions = MessageProcessor._extract_questions(text)
        assert clean == text
        assert questions == []

    def test_single_question(self):
        text = "Отличные места!\n[Q] Какой у вас бюджет?"
        clean, questions = MessageProcessor._extract_questions(text)
        assert clean == "Отличные места!"
        assert questions == ["Какой у вас бюджет?"]

    def test_multiple_questions(self):
        text = (
            "Я подобрал несколько мест.\n"
            "[Q] Какой у вас бюджет на день?\n"
            "[Q] С кем вы планируете поездку?"
        )
        clean, questions = MessageProcessor._extract_questions(text)
        assert clean == "Я подобрал несколько мест."
        assert len(questions) == 2
        assert questions[0] == "Какой у вас бюджет на день?"
        assert questions[1] == "С кем вы планируете поездку?"

    def test_question_without_question_mark(self):
        text = "Ответ.\n[Q] Какой бюджет"
        clean, questions = MessageProcessor._extract_questions(text)
        assert questions == ["Какой бюджет?"]

    def test_question_with_question_mark(self):
        text = "Ответ.\n[Q] Какой бюджет?"
        clean, questions = MessageProcessor._extract_questions(text)
        assert questions == ["Какой бюджет?"]

    def test_questions_between_text(self):
        text = (
            "Начало ответа.\n"
            "[Q] Первый вопрос?\n"
            "Продолжение текста.\n"
            "[Q] Второй вопрос?"
        )
        clean, questions = MessageProcessor._extract_questions(text)
        assert "Начало ответа." in clean
        assert "Продолжение текста." in clean
        assert "[Q]" not in clean
        assert len(questions) == 2

    def test_empty_question_ignored(self):
        text = "Текст.\n[Q] \n[Q] Реальный вопрос?"
        clean, questions = MessageProcessor._extract_questions(text)
        assert questions == ["Реальный вопрос?"]

    def test_empty_text(self):
        clean, questions = MessageProcessor._extract_questions("")
        assert clean == ""
        assert questions == []

    def test_only_questions(self):
        text = "[Q] Куда хотите поехать?\n[Q] На сколько дней?"
        clean, questions = MessageProcessor._extract_questions(text)
        assert clean == ""
        assert len(questions) == 2

    def test_preserves_formatting(self):
        text = (
            "**Рекомендации:**\n"
            "1. Парк Ривьера\n"
            "2. Дендрарий\n\n"
            "[Q] Какой бюджет?"
        )
        clean, questions = MessageProcessor._extract_questions(text)
        assert "**Рекомендации:**" in clean
        assert "1. Парк Ривьера" in clean
        assert "2. Дендрарий" in clean
        assert questions == ["Какой бюджет?"]
