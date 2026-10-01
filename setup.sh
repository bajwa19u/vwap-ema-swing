#!/usr/bin/env bash
# One-time setup: creates the private GitHub repo, pushes, and stores the
# three secrets. gh prompts you for each value; nothing is echoed or saved locally.
set -euo pipefail
cd "$(dirname "$0")"
gh auth status >/dev/null 2>&1 || gh auth login
REPO="${1:-vwap-ema-swing}"
gh repo view "$REPO" >/dev/null 2>&1 || gh repo create "$REPO" --private --source=. --remote=origin
git config http.postBuffer 524288000
git push -u origin HEAD
for s in ALPACA_API_KEY ALPACA_API_SECRET DISCORD_WEBHOOK_VWAP; do
  echo "Paste $s (input hidden), then Enter:"
  gh secret set "$s"
done
gh workflow run hello.yml
echo "Done. A test card should appear in your Discord channel within ~1 minute."
