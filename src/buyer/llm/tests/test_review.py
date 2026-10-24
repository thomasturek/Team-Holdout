from buyer.llm.review import fixtures, report


class FakeArena:
    """Only the three read calls review.py may use - nothing else exists here."""

    def sessions(self, set_):
        return [{"session_id": "s1", "case_id": "case:P01", "status": "ended", "created_at": "2026-10-24T10:00:00"},
                {"session_id": "s2", "case_id": "case:P02", "status": "open", "created_at": "2026-10-24T11:00:00"}]  # fmt: skip  # noqa: E501

    def session(self, sid):
        return {"session_id": sid, "end_reason": "accepted", "replay_url": "/replay/s1", "threads": {"sup:70110": {}},
                "result": {"score": 0.5, "deal": True, "supplier_id": "sup:70110",
                           "trace": [{"round": 1, "actor": "sup:70110", "reasons": ["Energy is bought forward."]}]}}  # fmt: skip  # noqa: E501

    def thread(self, sid, sup):
        return {"messages": [
            {"from": "sales@70110", "status": "open", "body": "Our quote is attached.", "claim_results": []},
            {"from": "buyer", "body": "Electricity fell (idx:PPI-D351@2026-08).", "refs": ["idx:PPI-D351@2026-08"],
             "term_sheets": [{"terms": {"unit_price": 120.0}}]},
            {"from": "sales@70110", "status": "final_offer", "claim_results": [{"index": 0, "result": "verified"}],
             "body": "That is not our reality. This is our final offer."},
        ]}  # fmt: skip


def test_report_flags_bad_reactions():
    md = report("practice", 10, client=FakeArena())
    assert "case:P01" in md and "case:P02" not in md  # only ended sessions
    assert "final_offer" in md and "not_our_reality" in md and "Energy is bought forward." in md
    assert "Electricity fell" in md.split("## Our e-mails that preceded a bad reaction")[1]


def test_fixture_export():
    out = fixtures("practice", 10, client=FakeArena())
    assert len(out["emails"]) == 2
    last = out["emails"][-1]
    assert last["expected"]["final_offer_language"] is True
    assert last["expected"]["rejected_args"] == ["idx:PPI-D351@2026-08"]
