# Windows packaging (portable only)

Release order (automated in `.github/workflows/release.yml`):

1. `python bx.py build win-x64`: Chromium `chrome` + `mini_installer` targets.
2. Extract the application files: `chromium\src\out\Release-x64\chrome.7z` contains
   `Chrome-bin\` (with the branding patch: `browserx.exe` plus the `<chromium-version>\` dir).
   Use Chromium's bundled `third_party\lzma_sdk\bin\win64\7za.exe x chrome.7z -ostaging`.
3. Build the launcher: `cmake -S launcher -B out\launcher -A x64 -DBX_REQUIRE_SIGNED=ON`
   then `cmake --build out\launcher --config Release`.
4. Sign every PE file: `sign.ps1 -Path staging\Chrome-bin, out\launcher\Release\BrowserX.exe`.
5. `python bx.py package win-x64 --staging staging\Chrome-bin --launcher out\launcher\Release\BrowserX.exe --notices out\Release-x64\gen\components\resources\about_credits.html`
   creates `dist\BrowserX\`, the zip, and `SHA256SUMS`.
6. `make-sfx.ps1 -Zip dist\BrowserX-<ver>-win-x64-portable.zip -SevenZip <7z.exe> -SfxModule <7z.sfx>`
   creates the one-file download, which asks where to extract.
7. `sign.ps1 -Path dist\BrowserX-<ver>-win-x64-portable.exe`
8. `python bx.py checksums dist\*.zip dist\*.exe`, then sign `SHA256SUMS` (decision D6).

The self-extractor uses 7-Zip's GUI SFX module `7z.sfx` (LGPL-2.1, credited in
THIRD_PARTY_NOTICES). It shows a "choose folder" dialog. We deliberately do **not** use an
"installer" SFX (such as `7zSD.sfx`) that extracts to `%TEMP%` and runs a program
automatically. Running from temp would break portable data rules and IT path-based controls.

Verify every step's paths against the pinned Chromium tag in Phase 0.
