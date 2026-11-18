from itops_rag.core.redact import RedactionReport, Redactor


def test_secrets_and_pii_are_masked() -> None:
    text = (
        "Key AKIAFAKE0000EXAMPLE and ghp_FAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE1234 and sk-test-FAKE0000000000000000000000\n"
        "password: Hunter2-FAKE\nCall +46 70 123 45 67 or mail jane.doe@kestrelcloud.example\n"
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789\n"
        "-----BEGIN RSA PRIVATE KEY-----\nFAKE\n-----END RSA PRIVATE KEY-----"
    )
    report = RedactionReport()
    out = Redactor().redact(text, "D1", report)
    for leaked in (
        "AKIAFAKE",
        "ghp_FAKE",
        "sk-test",
        "Hunter2",
        "+46 70",
        "jane.doe",
        "abcdefghijkl",
        "BEGIN RSA",
    ):
        assert leaked not in out, leaked
    assert "password: [REDACTED:password]" in out
    assert report.counts["email"] == 1
    assert report.per_doc["D1"]["aws_access_key"] == 1


def test_functional_mailboxes_are_kept() -> None:
    r = Redactor(keep_emails=[r"^servicedesk@"])
    assert "servicedesk@kestrelcloud.example" in r.redact("Mail servicedesk@kestrelcloud.example")


def test_ips_only_when_asked() -> None:
    r = Redactor()
    assert "10.20.14.88" in r.redact("host 10.20.14.88")
    assert "10.20.14.88" not in r.redact("host 10.20.14.88", extra_kinds=frozenset({"ipv4"}))


def test_error_codes_are_not_mistaken_for_secrets() -> None:
    text = "AADSTS53003, 0x80180014, MG-401, HELP-1042, CHG-2026-0003"
    assert Redactor().redact(text) == text


def test_phone_numbers_are_fully_masked_even_before_punctuation() -> None:
    r = Redactor()
    for number in ("+44 7700 900123", "+1 512 555 0147", "+46 70 123 45 67", "+351 912 345 678"):
        assert r.redact(f"call {number}. Thanks") == "call [REDACTED:phone]. Thanks"
