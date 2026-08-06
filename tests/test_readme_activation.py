from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_documents_one_fee_decision_activation_path() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for phrase in [
        "Ask whether to send Bitcoin now",
        "get_fee_recommendation",
        "send now or wait",
        "SATOSHI_API_URL",
        "public Satoshi API previously hosted at `bitcoinsapi.com` is paused",
        "Star this repo",
        "showcase",
    ]:
        assert phrase in readme
