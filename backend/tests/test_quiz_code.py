"""代码题答案只做文本规范化比较，不执行用户代码。"""

from app.agents.quiz import normalize_question
from app.routers.websocket import _answers_match, _normalize_code_text, _serialize_question_answer


def test_code_answer_normalizes_fence_indent_and_newlines():
    expected = "class User:\n    pass"
    submitted = "```python\r\n    class User:\r\n        pass\r\n```"
    assert _normalize_code_text(submitted) == expected
    assert _answers_match("code", submitted, expected)


def test_code_answer_does_not_treat_empty_answer_as_correct():
    assert not _answers_match("code", "", "")


def test_code_answer_serializes_mapping_for_text_column():
    assert _serialize_question_answer({"code": "print(1)"}) == '{"code": "print(1)"}'


def test_empty_non_code_answers_are_not_marked_correct():
    assert not _answers_match("fill", "", "")
    assert not _answers_match("fill", None, None)
    assert _answers_match("fill", 0, 0)


def test_normalize_nested_python_class_answer_and_explanation():
    question = normalize_question(
        {
            "question": "实现一个用户类",
            "type": "python_class",
            "answer": {"solution": {"code": "```python\nclass User:\n    pass\n```"}},
            "explanation": ["定义类", "保留构造接口"],
        }
    )
    assert question["question_type"] == "code"
    assert question["answer"] == "class User:\n    pass"
    assert question["explanation"] == "定义类\n保留构造接口"


def test_normalize_infers_code_type_from_nested_answer():
    question = normalize_question(
        {
            "question": "实现类",
            "answer": {"solution": {"code": "class User:\n    pass"}},
        }
    )
    assert question["question_type"] == "code"
    assert question["answer"] == "class User:\n    pass"
