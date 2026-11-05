from app.modules.library.library_groups import specific_group, groups


def test_abdala_uses_vaccine_group_from_source_ancestry():
    label = specific_group(
        {
            "chapter_no": "X",
            "linearization_uri": "http://id.who.int/icd/release/11/mms/1265228078",
        }
    )
    assert label and "vắc" in label.lower()


def test_unknown_entries_do_not_get_inferred_groups():
    assert specific_group({"chapter_no": "X", "linearization_uri": "unknown"}) is None
    assert specific_group({"chapter_no": "14", "linearization_uri": "unknown"}) is None


def test_group_index_has_no_dangling_or_empty_labels():
    data = groups()
    assert len(data["members"]) == 17710
    assert all(data["labels"].get(group, "").strip() for group in data["members"].values())
