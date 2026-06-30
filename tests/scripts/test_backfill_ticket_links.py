def test_parse_links_extracts_outward_and_inward_pairs():
    from scripts import backfill_ticket_links as bl
    src = "TS-1"
    links_json = (
        '[{"type":"Blocks","outward":"TS-2","inward":null},'
        ' {"type":"Duplicates","outward":null,"inward":"TS-3"}]'
    )
    pairs = bl.parse_links(src, links_json)
    assert ("TS-1", "TS-2", "blocks") in pairs
    assert ("TS-1", "TS-3", "duplicates") in pairs

def test_parse_links_normalizes_link_type_to_lowercase_snake():
    from scripts import backfill_ticket_links as bl
    pairs = bl.parse_links("TS-1", '[{"type":"Relates To","outward":"TS-9"}]')
    assert pairs and pairs[0][2] == "relates_to"

def test_parse_links_handles_empty_and_malformed():
    from scripts import backfill_ticket_links as bl
    assert bl.parse_links("TS-1", "") == []
    assert bl.parse_links("TS-1", "[]") == []
    assert bl.parse_links("TS-1", "not-json") == []
