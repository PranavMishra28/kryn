# Releasing KRYN

The public release gate is [supervised v1 qualification](v1-qualification.md). The [status table](../plan.md) must link actual final-artifact receipts for every required row. Frozen autonomous/UI research failures remain disclosed; they are not a supervised-v1 pass criterion.

1. Screen the supervised coding, browser/search, continuity, guard and sustained-use gates on a clean, committed **private candidate**. Candidate results find defects; they do not qualify a later wheel. Keep the public version and tags unchanged. Review the tracked tree and Git history with a redacting secret scanner; inspect every finding without copying raw secrets into issues or commits. Review direct and transitive dependency resolutions, including the browser lock and optional install phases; a direct version pin alone is not a complete transitive lock.
2. After those screens pass, prepare a focused private release PR with the intended version in `pyproject.toml` and `src/kryn/__init__.py`, exact README installation commands, changelog, security and third-party notices. Run `make check` and `make package-smoke`; review the diff, pinned dependencies, licenses, permissions and CI result. Merge only green reviewed code. A private branch version is not a published release.
3. On the final clean `main` commit, build with `python3 -B build_package.py --out-dir dist`. Record the commit and `dist/SHA256SUMS`; inspect the wheel manifest and verify `(cd dist && shasum -a 256 -c SHA256SUMS)`. For the owner install **before publication**, stage that exact wheel in a retained private environment and invoke the package's supported `kryn install` operation:

   ```sh
   wheel="$PWD/dist/kryn-1.0.0-py3-none-any.whl"
   wheel_sha="$(shasum -a 256 "$wheel" | cut -d ' ' -f1)"
   root="$HOME/Library/Application Support/LocalAI"
   candidate="$root/private-candidates/$wheel_sha"
   uv="$root/dependencies/uv-0.11.16/uv"
   if [ ! -x "$uv" ]; then uv="$(command -v uv)"; fi
   mkdir -p "$candidate"
   "$uv" venv --python 3.13 "$candidate/venv"
   "$uv" pip install --python "$candidate/venv/bin/python" --no-index --no-deps "$wheel"
   "$candidate/venv/bin/python" -E -B -m kryn --package-check
   "$candidate/venv/bin/python" -E -B -m kryn install
   ```

   Keep `$candidate` intact through rollback and reactivation because the installed launcher references its interpreter. Run **all** [supervised-v1 qualification gates](v1-qualification.md) from this final wheel, including startup, coding, browser/search, compaction/restart, resource recovery, sustained use, saved-session migration, update/rollback and reactivation. Public `install-kryn.py --tag` cannot be tested before the release exists; its anonymous bootstrap is step 5. A prior private candidate pass is not a final-artifact pass. If any gate fails, fix it in a new PR and restart final-artifact checks from the new commit.
4. Tag the exact qualified commit as `vX.Y.Z`, push the tag, then publish the wheel, `install-kryn.py` and `SHA256SUMS` as one GitHub release. Check that the published assets equal the qualified local hashes. The release description must state supervised scope, supported hardware, known autonomous limits and rollback instructions.
5. From an anonymous HTTP client, download the published installer and assets over HTTPS, verify hashes, and perform a fresh install or update using the documented command. Record the result in [historical evidence](history.md). If publication or anonymous verification fails, leave the release marked unqualified and repair it explicitly.

The wheel builder rejects dirty source unless `--candidate` is passed. Candidate builds are for private checks only and must never be published. The installer verifies HTTPS downloads, release checksum, curated payload hashes and pinned dependencies; checksum assets rely on the authenticated publisher and are not independent signatures. Before explicitly retiring an old public release, archive its assets, metadata and Git refs and retain the current install route until a replacement is qualified.
