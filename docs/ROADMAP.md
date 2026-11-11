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
- [x] Add fixed-name outer ZIP package with encrypted .fckey metadata
- [x] Add rename-independent package detection and video payload extraction path
- [ ] Verify real WinRAR RAR5 creation/extraction behavior on Windows
- [x] Add optional real-tool end-to-end test for split volumes, dual passwords and arbitrary renamed output
- [x] Add batch folder packaging and multi-package restoration
- [x] Disable the single-video selector in batch mode

## 0.3 — release preparation
- [x] Add PyInstaller Windows executable build
- [x] Add Windows portable ZIP workflow
- [x] Add Inno Setup installer workflow
- [x] Add .fc file association (installer registers it; app accepts the opened path)
- [x] Embed the app icon in the Windows executable and installer
- [ ] Improve extraction progress and cancellation cleanup UX
- [ ] Add per-item batch progress and retry/report export
- [ ] Complete developer avatar and About-page presentation
- [ ] Execute real 7-Zip + WinRAR end-to-end tests on a Windows machine and record results
- [x] Move standalone .fckey Reader to the independent fcreader branch

## Video-payload compatibility
- [ ] Define and test a supported video-container/player matrix
- [ ] Validate playback and payload extraction on actual target players
- [ ] Add corruption detection and clearer unsupported-container errors
- The current implementation appends a packaged payload and locator trailer to selected video bytes. It is a prototype, not a certified universal video polyglot.

## Security and format decisions
- metadata.fckey contains authenticated encrypted metadata. Two original layer passwords are verified before deriving printable external passwords; no derived archive password is stored in plaintext.
- Missing or modified split volumes are rejected before extraction.
- The outer ZIP uses fixed internal entries (metadata.fckey, payload.rar); output filename and extension are not used to infer the internal package layout.
- Extraction validates archive paths and stages output before moving results.
- 7-Zip and WinRAR CLI password arguments may be visible to local process inspection tools. This prototype is not a hardened high-assurance vault.
- File associations are installed per Windows file type by the corresponding installer and removed by its uninstaller.