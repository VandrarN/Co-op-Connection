Co-op Connection — Vertical Slice (Content Loader)

This version replaces demo_text() with a real ContentManager that loads texts from:
  content/*.json

Important:
- The included content files are placeholders in this package.
- Replace the JSON lists with your own question packs to avoid spoilers.

Controls:
- Mouse: click buttons and decks (when Free shows "Choose a Card")
- Keyboard: R=Roll, D=Draw, N=Next, S=Skip, M=Mirror, ESC=Quit
- Title: ENTER starts, TAB switches name field.

Build EXE (Windows 11):
- Double click build_windows.bat
- Output: dist\CoOpConnection_VerticalSlice_ContentLoader.exe

Packaging:
- Uses --add-data "content;content" so JSON files are bundled into the exe.


This build includes full real question decks in content/*.json.
