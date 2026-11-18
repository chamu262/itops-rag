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


def test_reviewer_bypass_cases_are_masked() -> None:
    r = Redactor()
    cases = {
        "aws_secret_access_key = FAKEsecretFAKEsecretFAKEsecretFAKE0000": "FAKEsecret",
        'export DB_PASSWORD="S3cr3t!"': "S3cr3t",
        "AZURE_CLIENT_SECRET=abc8Q~FAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFA": "Q~FAKE",
        "key sk-ant-api03-FAKEFAKEFAKEFAKEFAKEFAKEFAKE-xyz": "sk-ant",
        "Authorization: Basic dXNlcjpwYXNzd29yZA==": "dXNlcj",
        "token eyJhbGciOiJub25lIn0.eyJzdWIiOiJ4In0.": "eyJ",
        "-----BEGIN OPENSSH PRIVATE KEY-----\nAAAAFAKE\nBBBBFAKE": "AAAAFAKE",
        "Password = 'p@ss w0rd' done": "w0rd",
        "AWS secret: aws_secret_access_key = FAKEKEY123456": "FAKEKEY",
        "call 070-123 45 67 or 07700 900123.": "123 45",
    }
    for text, leaked in cases.items():
        assert leaked not in r.redact(text), text


def test_keep_list_is_tied_to_the_domain() -> None:
    r = Redactor(keep_emails=[r"^security@kestrelcloud\.example$"])
    assert r.redact("security@evil.example.com") == "[REDACTED:email]"
    assert r.redact("security@kestrelcloud.example") == "security@kestrelcloud.example"


def test_no_fixture_secret_survives_ingest(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from itops_rag import Index, Settings
    from itops_rag.core.embeddings import HashEmbedder
    from tests.conftest import DEMO

    s = Settings(index_dir=tmp_path / "ix", store="sqlite", cost_ledger=tmp_path / "c", _env_file=None)  # type: ignore[call-arg]
    with Index.open(s, embedder=HashEmbedder(), reranker=False) as ix:
        ix.ingest_path(DEMO / "adversarial")
        ix.ingest_path(DEMO / "tickets")
        text = "\n".join(r[0] for r in ix.docs.conn.execute("SELECT text FROM chunks").fetchall())
    for secret in (
        "AKIAFAKE",
        "FAKEsecret",
        "Hunter2",
        "ghp_FAKE",
        "sk-test-FAKE",
        "BEGIN PRIVATE KEY",
        "+46 70 123",
        "+44 7700",
        "10.20.14.88",
    ):
        assert secret not in text, secret
