# QuanX Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Publish an independent repository that synchronizes every upstream classification to QuanX daily.

**Architecture:** A standard-library Python package converts one immutable sing-branch snapshot into a staged output tree and validates its catalog before replacing the destination. One Actions workflow tests, generates, and commits changes to a dedicated quanx branch; publication never uses a force push.

**Tech Stack:** Python 3.12+, unittest, Git, GitHub Actions.

**Spec:** docs/superpowers/specs/2026-10-27-quanx-rules-design.md

## Global Constraints

- Include all JSON categories, including asn, geo and geo-lite, without a category whitelist.
- Schedule daily at 08:30 Asia/Shanghai (00:30 UTC), allow manual trigger.
- Preserve unsupported regex entries in reports; unknown conditions abort publication.
- Deterministic output, stable URLs on quanx branch, no personal token requirement.
- Keep existing output unchanged on conversion failure and fail on a suspicious drop in classification count.
- User authorized implementation and GitHub upload; execute inline without further approval prompts.

## Review Focus

- A truncated archive or duplicate source member must never publish a partial ruleset.
- Unknown match constraints must never be flattened into broader matching rules.
- Invalid data following a valid file must leave an existing output tree intact.
- Rerunning a snapshot must leave byte-identical outputs and create no publication commit.
- A failed push or missing credentials must be reported as failure, not successful publication.

### Task 1: Conversion semantics

**Files:** Create quanx_rules/convert.py, quanx_rules/__init__.py; test tests/test_convert.py.

**Interfaces:** Produces ConversionError and convert_document(document: dict) -> Conversion(lines: list[str], unsupported: list[dict], source_entries: int). Canonical policy is proxy. Lines contain no header or timestamp. domain_regex entries are retained as unsupported.

- [x] Write failing tests covering domain/full suffix/leading-dot suffix/keyword, string and array forms, IPv4/IPv6 normalization and de-duplication, regex-only and empty inputs, injection and unknown/logical constraints.
- [x] Run python3.12 -m unittest tests.test_convert -v; expect missing converter errors until the interface exists, then assertion failures for incomplete conversion.
- [x] Implement scalar normalization, strict supported-key/shape validation, host/host-suffix/host-wildcard mappings and CIDR conversion; reject ambiguity.
- [x] Run python3.12 -m unittest discover -v; expect all tests passing.
- [x] Commit conversion and tests.

### Task 2: Complete snapshots and deterministic catalog

**Files:** Create quanx_rules/build.py, quanx_rules/upstream.py, quanx_rules/__main__.py; test tests/test_build.py and tests/test_upstream.py.

**Interfaces:** Consumes convert_document. Produces build_archive(archive: Path, output: Path, sha: str, repository: str) -> dict summary; resolve_snapshot() -> str; download_snapshot(sha: str, destination: Path) -> None. CLI supports --archive and --sha for reproducible offline builds and downloads a pinned snapshot otherwise.

- [x] Write failing integration tests with real miniature tarballs, including unexpected JSON directories, traversal, duplicate members, corrupted/truncated gzip, supported/partial/unsupported-only/empty categories, valid links, deterministic output, replacement/removal and preserving old output on error.
- [x] Write offline HTTP tests for commit resolution, retries and incomplete download handling using a local server.
- [x] Run new tests and confirm missing build/download behavior.
- [x] Implement archive scan without extraction, atomic staging, source SHA and provenance, sharded manifests and paged Markdown indexes, nonempty rule files and full regex reports; verify every category and rule line before publication.
- [x] Implement bounded retries/timeouts for official GitHub endpoints; keep cache outside output. Require the known source directory families to exist and reject >20% classification loss compared with existing reports/summary.json by default; provide a documented explicit override for intentional upstream removals.
- [x] Run all unittest tests; expect pass. Commit.

### Task 3: Publishing, workflow and user documentation

**Files:** Create quanx_rules/publish.py, tests/test_publish.py, .github/workflows/update.yml, README.md, LICENSE, THIRD_PARTY.md.

**Interfaces:** Consumes generated output directory. Produces publish(output: Path, remote: str, branch: str = 'quanx') -> bool: true only if a commit was pushed; raises on failed fetch/push. CLI accepts output and remote. Fetch existing branch or identify truly absent branch via ls-remote; never swallow network/auth failures.

- [x] Write failing integration tests using temporary local bare repositories: initial publication, unchanged rerun, changed/removal publication, push failure and fetch error.
- [x] Implement temporary isolated publishing checkout with ordinary commits/push and fixed bot identity; never include secret values in exceptions or logs.
- [x] Add a single workflow with schedule, workflow_dispatch and code push triggers; tests always run and publishing is restricted to trusted main branch runs, not pull requests. Scope write token to publishing job only; serialize updates and report all compatibility counts.
- [x] Write Chinese setup/subscription/local usage documents, explicit empty/regex caveats and source attribution. Preserve upstream GPL-3.0 license and identify upstream data provenance without asserting all external sources have the same license.
- [x] Run unittest suite and workflow validation. Commit.

### Task 4: Real-data validation, review and GitHub deployment

**Files:** Update docs/verification.md and README.md with actual repository URLs; finalize tracked plan checkboxes.

**Interfaces:** Uses all preceding tasks. Remote target akaagiao1/quanx-rules (new public repository for directly accessible rule subscriptions).

- [x] Run full source archive conversion; record source SHA, category/status/rule counts, elapsed time and disk usage.
- [x] Run a second conversion and compare file hashes; validate indexes and generated rule syntax via builder checks.
- [x] Request a fresh read-only whole-project code review, fix Important/Critical findings with regression tests and a passing full suite.
- [ ] Verify suite and workflow configuration, create public GitHub repo, upload source, dispatch workflow if needed, and inspect its result until the first quanx publication succeeds.
- [ ] Inspect published summary, several real subscription URLs and workflow schedule; deliver repo URL and concise usage. Do not claim QuanX device testing.
