from src.audience_analytics import activity_score, audience_overlap, campaign_signals, enrich_members, snapshot_delta


def test_activity_score_and_segments_are_observable_only():
    member = {"comments": 2, "replies": 1, "polls": 1, "known_reactions": 2, "channels_count": 3}
    assert activity_score(member) == 2 * 5 + 1 * 4 + 1 * 3 + 2 * 2
    row = enrich_members([member])[0]
    assert row["activity_score"] == 21
    assert row["views_attributed"] is False
    assert "مجهولة" in row["privacy_note"]


def test_overlap_delta_and_campaign_signal():
    overlap = audience_overlap({"أخبار": ["1", "2"], "تقنية": ["2", "3"]})
    assert overlap["pairwise"][0]["shared"] == 1
    assert overlap["all_channels"] == 1
    assert snapshot_delta({"أخبار": 10}, {"أخبار": 14, "تقنية": 2})["أخبار"]["delta"] == 4
    signals = campaign_signals([{"channel_id": "a", "message_id": 1}], [{"channel_id": "a", "period": "24h", "subscribers_before": 10, "subscribers_after": 12}])
    assert signals[0]["candidate_posts"] == [1]
    assert "سببيًا" in signals[0]["interpretation"]
