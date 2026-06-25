import pytest
from scripts.lib.ref_classify import classify_url


@pytest.mark.parametrize("url,expected_type,expected_id", [
    ("https://docs.google.com/document/d/11Meiq_ABC/edit", "gdoc", "11Meiq_ABC"),
    ("https://docs.google.com/spreadsheets/d/1FyWu-DnS/edit#gid=0", "gsheet", "1FyWu-DnS"),
    ("https://docs.google.com/presentation/d/1CcHEQ_x/edit#slide=id.g1", "gslide", "1CcHEQ_x"),
    ("https://moveinsync.atlassian.net/browse/PB-49903", "jira", None),
    ("https://moveinsync.atlassian.net/issues/PB-46642", "jira", None),
    ("https://mis-security.moveinsync.com/mis-security-guard/premise", "api", None),
    ("https://signup.eu.workinsync.io/", "api", None),
    ("http://ec2-54-255-90-58.ap-southeast-1.compute.amazonaws.com:9045/x", "api", None),
    ("https://jsonformatter.org/", "external", None),
    ("mailto:abc@xyz.com", "external", None),
])
def test_classify(url, expected_type, expected_id):
    t, fid = classify_url(url)
    assert (t, fid) == (expected_type, expected_id)
