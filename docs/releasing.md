# Release a package

1. Update the version in `pyproject.toml`, `src/bitcoin_mcp/__init__.py`, and both version fields in `server.json`. Update installation instructions when needed.
2. Run `uv run --extra dev --extra l402 pytest tests/` on each supported Python version in the test workflow.
3. Build from the reviewed release commit with `uv build`, then run `uvx twine check dist/*`.
4. Install the wheel with its `l402` extra and pytest into a fresh virtual environment. Run the repository tests using that environment, with the working directory outside the checkout, and confirm `bitcoin_mcp.__file__` points to the installed wheel.
5. Publish the two artifacts with `uvx twine upload dist/*`, using credentials configured outside the repository. Never commit publishing credentials.
6. Read back the new version from PyPI and check its dependency requirements and artifact hashes. Create a GitHub release tagged `v<version>` at the same commit, with the user-visible fixes and validation results.

PyPI versions are immutable. If a published version needs a correction, prepare a new patch version instead of replacing an artifact. Keep the source tag, package metadata, and registry manifest aligned.
