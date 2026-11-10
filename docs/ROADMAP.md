# Development roadmap

## 0.1 — first usable desktop build
- [x] Qt desktop shell with restrained neutral styling
- [x] Source selection, optional video association, output directory
- [x] Automatic 1 / 2 / 3 GiB volume policy
- [x] 7-Zip encrypted archive creation and extraction
- [x] Password-protected authenticated .fc manifest
- [x] SHA-256 validation of archive volumes

## 0.2 — usability and extraction hardening
- [x] Persist 7-Zip path, output folders and window geometry
- [x] Parse 7-Zip percentage output into a real progress bar
- [x] Cancel running archive operations without freezing the UI
- [x] Prevent accidental overwrite of existing package outputs
- [x] Extract into a temporary staging directory before moving results
- [x] Reject absolute paths, traversal, unsafe Windows names, duplicate case-insensitive names and archive links
- [x] Reject symlinks in input trees and validate package filenames
- [x] Allow cancellation during archive-volume hashing
- [x] Add Windows + Ubuntu GitHub Actions test workflow
- [ ] Verify behavior with real 7-Zip builds on Windows
- [x] Add WinRAR executable discovery and cancellable command execution
- [x] Implement the 7z-volume directory -> RAR5 AES-256 second-layer pipeline
- [x] Add fixed-name outer ZIP package with encrypted `.fckey` metadata
- [x] Add rename-independent package detection and video payload extraction path
- [ ] Verify real WinRAR RAR5 creation/extraction behavior on Windows

## 0.3 — release preparation
- [ ] Add packaging workflow (PyInstaller) and a Windows portable build
- [ ] Improve extraction progress and cancellation cleanup UX
- [ ] Add password confirmation and password-strength guidance
- [ ] Add application icon and file association for .fc
- [ ] Add end-to-end tests using real 7-Zip + WinRAR, including split archives and arbitrary output renaming
- [ ] Implement standalone `.fckey` Reader UI / executable

## Format and security decisions
- The current video-payload prototype appends a packaged payload and a locator trailer to the selected video bytes. Compatibility must be tested against actual target players and containers; this is not yet certified as a universal video polyglot.
- .fc contains an authenticated encrypted manifest. The master password derives a per-package archive password; no archive password is stored in plaintext.
- Missing or modified split volumes are rejected before extraction.
- The outer ZIP uses fixed internal entries (`metadata.fckey`, `payload.rar`); output filename and extension are not used to infer the internal package layout.
- Extraction validates archive paths and stages output before moving it into the destination.
- 7-Zip CLI password arguments may be visible to local process inspection tools. This prototype is not a hardened high-assurance vault.
