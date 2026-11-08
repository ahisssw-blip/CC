from src.editor_analytics import editorial_report


def test_editorial_report_explains_views_and_reactions():
    report = editorial_report([
        {'id': 1, 'channel_title': 'أخبار', 'date': '2026-01-01 10:00:00', 'views': 1000, 'reaction_count': 1, 'media_type': 'Photo'},
        {'id': 2, 'channel_title': 'أخبار', 'date': '2026-01-01 11:00:00', 'views': 10, 'reaction_count': 10, 'media_type': 'text'},
    ])
    assert report['total'] == 2
    assert report['summary']['top_hour'] == '10'
    assert report['summary']['top_media_type'] == 'Photo'
    assert 'ليست إثباتًا' in report['causality_note']
