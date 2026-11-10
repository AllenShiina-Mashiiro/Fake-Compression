# Development roadmap

## 0.1 — first usable desktop build
- [x] Qt desktop shell with restrained neutral styling
- [x] Source selection, optional video association, output directory
- [x] Automatic 1 / 2 / 3 GiB volume policy
- [x] 7-Zip encrypted archive creation and extraction
- [x] Password-protected authenticated `.fc` manifest
- [x] SHA-256 validation of archive volumes
- [ ] Windows end-to-end smoke test with real 7-Zip installations

## 0.2 — hardening
- Persist settings and add optional WinRAR compatibility backend
- Add cancellation, determinate progress parsing, collision handling and atomic staging
- Add safer extraction checks for traversal and symlinks
- Add packaging workflow and release artifacts

## Format and security decisions
- The video remains a separate ordinary preview file. Archive bytes are never appended to it or used to disguise data.
- `.fc` contains an authenticated encrypted manifest. The master password derives a per-package archive password; no archive password is stored in plaintext.
- Missing or modified split volumes are rejected before extraction.
- 7-Zip CLI password arguments may be visible to local process inspection tools. Treat this initial version as a local prototype, not a hardened high-assurance vault.
