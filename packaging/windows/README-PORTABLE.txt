Browser-x (portable)
====================

Start the browser:   BrowserX.exe

Your data:           the Data folder next to BrowserX.exe (created on first run).
                     It holds your profile: history, bookmarks, cookies, cache and
                     settings. Nothing is stored in the registry or other folders,
                     apart from temporary files Windows may use.

Remove everything:   close Browser-x and delete this whole folder.

Moving the folder:   cookies and saved passwords are protected by Windows for your
                     user account and will not work on another account or computer.

Blocked by IT?       If you see "Your organization does not allow the portable
                     version", your administrator has disabled portable mode.
                     Use the browser your IT department approved.

Verify this copy:    Get-AuthenticodeSignature .\BrowserX.exe   (must be Valid)
                     Compare the download with SHA256SUMS from the release page.

More:                docs/portable-mode.md in the Browser-x source repository.
