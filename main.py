name: Build and deploy Co-op Connection

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install pygbag
        run: pip install pygbag

      - name: Build portrait web game
        run: python -m pygbag --build --width 900 --height 1350 .

      - name: Force fresh archive name
        run: |
          cp build/web/co-op-connection.tar.gz build/web/co-op-connection-debugtest.tar.gz

          python - <<'PY'
          from pathlib import Path

          index = Path("build/web/index.html")
          text = index.read_text()

          text = text.replace("co-op-connection.tar.gz", "co-op-connection-debugtest.tar.gz")
          text = text.replace('"archive":"co-op-connection"', '"archive":"co-op-connection-debugtest"')
          text = text.replace('"archive": "co-op-connection"', '"archive": "co-op-connection-debugtest"')
          text = text.replace("archive: 'co-op-connection'", "archive: 'co-op-connection-debugtest'")
          text = text.replace('archive: "co-op-connection"', 'archive: "co-op-connection-debugtest"')

          index.write_text(text)
          PY

      - name: Show build output after build
        run: |
          echo "=== BUILD FILES ==="
          find build/web -type f | sort

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: build/web

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages

    steps:
      - name: Deploy
        uses: actions/deploy-pages@v4
