# Changelog

## [0.1.0] - 2026-11-18

Initial public release of `workbuddy-supplement`:

- Added portable `skills/workbuddy-supplement/` skill (`SKILL.md`,
  `scripts/wb_supplement.py`, and `references/free-sources-guide.md`).
- Added cross-platform path auto-detection (`WORKBUDDY_CONFIG_DIR`,
  `WORKBUDDY_APP_DIR`, Windows/macOS/Linux default locations, and POSIX/Windows
  `westock` resolution).
- Implemented strict loopback-only `:8045` Zero-Cost Guard (`[ZERO_COST_GUARD]`,
  exit code `2`) on `wb-websearch` so neither default runs nor `WB_FREE_PROXY_URL`
  overrides can reach remote paid relays.
- Added `scripts/install.py` for clean installation, verification (`--check`),
  and removal (`--uninstall`) across Antigravity, Codex, Claude Code, or custom
  skill directories.
- Added stdlib offline test suite (`tests/test_wb_supplement.py`) and
  cross-platform GitHub Actions workflow (`ubuntu-latest` and `windows-latest`).
