#!/usr/bin/env bash
# For the repo owner: take a contributor's handoff branch, put it on main, build and publish the GitHub release.
#
#   bash build/release.sh [handoff branch]      (default: handoff/v<version in app/package.json>)
#
# Needs: git, gh (logged in: gh auth login) and what build/package.sh needs (bash, curl, npm, python3 + Pillow).
set -euo pipefail
cd "$(dirname "$0")/.."
command -v gh >/dev/null || { echo "release.sh needs the GitHub CLI: https://cli.github.com (then: gh auth login)" >&2; exit 1; }
git fetch -q origin
VERSION="$(git show "origin/${1:-HEAD}:app/package.json" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])" || true)"
BRANCH="${1:-handoff/v$VERSION}"
git rev-parse -q --verify "origin/$BRANCH" >/dev/null || { echo "No branch origin/$BRANCH on GitHub." >&2; exit 1; }
VERSION="$(git show "origin/$BRANCH:app/package.json" | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])")"
TAG="v$VERSION"
echo "== $BRANCH -> main, release $TAG"
git checkout -q main
git merge --ff-only "origin/$BRANCH"
git push origin main
# Zips already built (all four in dist): publish those; otherwise build them. Delete dist to force a rebuild.
if ls dist/R64texHD-$TAG-Windows.zip dist/R64texHD-$TAG-scenes.zip dist/R64texHD-$TAG-models.zip dist/R64texHD-$TAG-onnx.zip >/dev/null 2>&1; then
  echo "== Using the zips already in dist (delete dist to rebuild them)"
else
  bash build/package.sh
fi
NOTES="$(mktemp)"; sed -n "/^## $TAG\$/,/^## v/p" CHANGELOG.md | sed '1d;$d' > "$NOTES"
gh release create "$TAG" dist/R64texHD-$TAG-*.zip --target main --title "R64texHD $TAG" --notes-file "$NOTES"
rm -f "$NOTES"
echo "== Published $TAG"
