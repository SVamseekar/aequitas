"""Research pack CSV schema — English headers, score + caveats."""

import pytest

from aequitas.api.services.export_pack import CAVEATS, pack_csv, pack_payload

try:
    import aequitas.ireland  # noqa: F401

    _HAS_IRELAND = True
except ImportError:
    _HAS_IRELAND = False


def test_pack_csv_english_headers_and_caveats():
    payload = pack_payload(None, region="all", urban_rural="all")
    text = pack_csv(payload)
    assert text.startswith("Section,Item,Value")
    assert "In-country score" in text
    assert "Research pack, not a statutory BSIP submission." in text
    assert "Not TfL PTAL" in text
    assert "Official BSIP 2024 submission" not in text
    for c in CAVEATS:
        assert c in text


def test_pack_endpoint_csv(api_client):
    resp = api_client.get("/api/export/pack.csv?region=all&urban_rural=all")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    body = resp.text
    assert "Section,Item,Value" in body
    assert "Caveat" in body


def test_pack_endpoint_html(api_client):
    resp = api_client.get("/api/export/pack.html?region=E12000005&urban_rural=rural")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "statutory BSIP" in resp.text
    assert "Aequitas research briefing pack" in resp.text


@pytest.mark.skipif(not _HAS_IRELAND, reason="Ireland pack not on this branch")
def test_ireland_pack_csv_names_tfi_not_england():
    payload = pack_payload(None, region="all", urban_rural="all", country="ireland")
    body = pack_csv(payload)
    assert "BODS" not in body
    assert "England" not in body
    assert "TFI" in body
    assert "Small Areas" in body
    assert "Pobal HP" in body
    assert "Republic" in body


@pytest.mark.skipif(not _HAS_IRELAND, reason="Ireland pack not on this branch")
def test_ireland_pack_html_names_tfi_not_england():
    from aequitas.api.services.export_pack import pack_html

    payload = pack_payload(None, region="all", urban_rural="all", country="ireland")
    body = pack_html(payload)
    assert "BODS" not in body
    assert "England" not in body
    assert "TFI" in body or "Republic" in body
    assert "Pobal HP" in body or "Small Areas" in body


def test_nl_pack_404_france_pack_ok(api_client):
    assert api_client.get("/api/export/pack.csv?country=netherlands").status_code == 404
    fr = api_client.get("/api/export/pack.html?country=france")
    assert fr.status_code == 200
    assert "F-EDI" in fr.text or "IRIS" in fr.text or "NAP" in fr.text


def test_bands_london_rural_empty(api_client):
    resp = api_client.get("/api/reach/bands?region=E12000007&urban_rural=rural")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("empty") is True
    assert "London" in (body.get("empty_reason") or "")
