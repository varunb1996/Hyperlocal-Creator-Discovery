import logging

import pytest

from normalize import COLUMNS, UNMAPPED, load_creators, load_mappings, load_vocab, normalize


@pytest.fixture(scope="module")
def vocab():
    return load_vocab()


@pytest.fixture(scope="module")
def mappings(vocab):
    return load_mappings(vocab)


def test_all_creators_normalize_to_valid_vocab(vocab, mappings):
    creators = load_creators()
    assert len(creators) == 115

    rows = normalize(creators, mappings)

    unmapped = [(r["Username"], c) for r in rows for c, *_ in COLUMNS.values() if r[c] == UNMAPPED]
    assert unmapped == []
    for clean_name, vocab_key, _ in COLUMNS.values():
        invalid = {r[clean_name] for r in rows} - vocab[vocab_key]
        assert not invalid, f"{clean_name} has non-vocab values: {invalid}"


def test_occasionally_kept_distinct_from_yes_and_no(mappings):
    rows = normalize(load_creators(), mappings)
    occasional = [r for r in rows if r["Regularly Features Pune Venues?"] == "Occasionally"]
    assert len(occasional) == 9
    assert all(r["features_pune"] == "Occasionally" for r in occasional)


def test_unknown_value_is_flagged_and_logged(mappings, caplog):
    creator = {"Username": "@new", "Content Category": "Underwater Basket Weaving"}
    with caplog.at_level(logging.WARNING):
        row = normalize([creator], mappings)[0]
    assert row["content_category"] == UNMAPPED
    assert "Underwater Basket Weaving" in caplog.text
