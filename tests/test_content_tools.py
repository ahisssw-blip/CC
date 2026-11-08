from src.content_quality import analyze_posts, issue_summary, normalize_text
from src.content_similarity import find_similar_posts
from src.natural_query import parse_arabic_query


def test_quality_detects_duplicate_hashtag_and_duplicate_text():
    posts = [
        {"channel_id": "a", "message_id": 1, "raw_text": "خبر مهم #خبر #خبر"},
        {"channel_id": "b", "message_id": 2, "raw_text": " خبر مهم #خبر #خبر "},
    ]
    issues = analyze_posts(posts)
    summary = issue_summary(issues)
    assert summary["duplicate_hashtag"] == 2
    assert summary["duplicate_text"] == 1
    assert normalize_text("  سطر  \n\n\n  ثاني ") == "سطر\n\nثاني"


def test_similarity_and_arabic_query_are_explainable():
    matches = find_similar_posts([
        {"channel_id": "a", "message_id": 1, "raw_text": "الذكاء الاصطناعي يغير مستقبل العمل بسرعة"},
        {"channel_id": "b", "message_id": 2, "raw_text": "الذكاء الاصطناعي يغير مستقبل العمل بسرعة كبيرة"},
    ], threshold=0.7)
    assert matches and matches[0].score >= 0.7
    intent = parse_arabic_query('أرني منشورات قناة التقنية التي تحتوي على "الذكاء الاصطناعي" ولا تحتوي على صورة')
    assert intent.channel_name == "التقنية"
    assert intent.text == "الذكاء الاصطناعي"
    assert intent.must_have_media is False
