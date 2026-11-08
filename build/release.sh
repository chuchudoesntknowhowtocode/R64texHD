#!/usr/bin/env bash
# R64texHD — publish a release, start to finish (for the repo owner).
#
#   bash build/release.sh [handoff branch]
#
# 1. Checks the tools (git, gh logged in, python3).
# 2. Takes the contributor's handoff branch (default handoff/v<version>) onto main and pushes main.
# 3. Zips: uses the four zips already in dist/ if they're there, else builds them (build/package.sh).
# 4. Checks the zips: they open, and the Windows build's download links / checksums match the other three.
# 5. Writes the release notes (from CHANGELOG.md) and creates tag + release v<version> with the four zips.
#    Already published? It replaces the zips and the notes instead (safe to run again).
# 6. Checks every download link on GitHub.
set -euo pipefail
cd "$(dirname "$0")/.."
say() { printf '\n== %s\n' "$*"; }
die() { printf '\nSTOPPED: %s\n' "$*" >&2; exit 1; }

# ---- 1. tools
for t in git gh python3 curl; do command -v "$t" >/dev/null || die "needs $t on the PATH${t:+ }$( [ "$t" = gh ] && echo '(GitHub CLI: https://cli.github.com)')"; done
gh auth status >/dev/null 2>&1 || die "gh isn't logged in: run  gh auth login"
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null)" || die "gh can't see this repo (run it inside the R64texHD folder)"
ver_of() { git show "$1:app/package.json" | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])"; }

# ---- 2. branch -> main
say "Fetching $REPO"
git fetch -q origin
BRANCH="${1:-handoff/v$(ver_of origin/main)}"
if git rev-parse -q --verify "origin/$BRANCH" >/dev/null; then
  VERSION="$(ver_of "origin/$BRANCH")"
else
  echo "(no branch origin/$BRANCH: releasing main as it is)"; BRANCH=""; VERSION="$(ver_of origin/main)"
fi
TAG="v$VERSION"; NAME="R64texHD-$TAG"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "this folder has uncommitted changes; commit or stash them first"
git checkout -q main
git merge -q --ff-only origin/main || die "local main and GitHub main have split (different commits on both); sort that out by hand first"
[ -n "$BRANCH" ] && { say "Merging $BRANCH into main"; git merge --ff-only "origin/$BRANCH" || die "$BRANCH can't fast-forward main; merge it by hand"; }
[ "$(ver_of HEAD)" = "$VERSION" ] || die "version mismatch"
say "Pushing main"
git push origin main

# ---- 3. zips
ZIPS=("dist/$NAME-Windows.zip" "dist/$NAME-scenes.zip" "dist/$NAME-models.zip" "dist/$NAME-onnx.zip")
if ls "${ZIPS[@]}" >/dev/null 2>&1; then
  say "Using the zips already in dist (delete dist to rebuild them)"
else
  say "Building $NAME (build/package.sh)"
  bash build/package.sh
fi
ls "${ZIPS[@]}" >/dev/null 2>&1 || die "missing zips in dist: ${ZIPS[*]}"

# ---- 4. check the zips
say "Checking the zips"
python3 - "$REPO" "$TAG" "$NAME" "${ZIPS[@]}" <<'PY' || die "the zips don't match each other: delete dist and run again to rebuild"
import hashlib, json, sys, zipfile
repo, tag, name, win, *packs = sys.argv[1:]
for z in [win, *packs]:
    bad = zipfile.ZipFile(z).testzip()
    if bad: sys.exit(f'{z}: broken file {bad}')
with zipfile.ZipFile(win) as z:
    names = set(z.namelist())
    if f'{name}/R64texHD.exe' not in names: sys.exit(f'{win}: no {name}/R64texHD.exe')
    app = json.loads(z.read(f'{name}/resources/app/package.json'))
    if 'v' + app['version'] != tag: sys.exit(f'{win}: app version {app["version"]}, not {tag}')
    for kind in ('scenes', 'models', 'onnx'):
        rj = json.loads(z.read(f'{name}/resources/app/assets/{kind}/remote.json'))
        pack = next(p for p in packs if p.endswith(f'-{kind}.zip'))
        want_url = f'https://github.com/{repo}/releases/download/{tag}/{name}-{kind}.zip'
        sha = hashlib.sha256(open(pack, 'rb').read()).hexdigest()
        if rj['url'] != want_url: sys.exit(f'{kind}: the app downloads {rj["url"]}, expected {want_url}')
        if rj['sha256'] != sha: sys.exit(f'{kind}: {pack} is not the file this build expects (checksum)')
        print(f'  {kind:7} ok  {rj["size"] / 1e6:6.1f} MB')
print(f'  Windows ok  ({len(names)} files, version {app["version"]})')
PY

# ---- 5. notes + release
NOTES="dist/RELEASE-NOTES-$TAG.md"
{
  echo "**Download \`$NAME-Windows.zip\`**, unzip it anywhere and run \`R64texHD.exe\` (portable, no install)."
  echo "The other zips are optional extras the app downloads itself from Settings: scenes, texture models, ONNX engine."
  echo
  sed -n "/^## $TAG\$/,/^## v/p" CHANGELOG.md | sed '1d;$d'
  echo
  echo "Full history: [CHANGELOG.md](https://github.com/$REPO/blob/$TAG/CHANGELOG.md)"
} > "$NOTES"
[ "$(grep -c . "$NOTES")" -gt 4 ] || die "no '## $TAG' section in CHANGELOG.md"
if gh release view "$TAG" >/dev/null 2>&1; then
  say "Release $TAG exists: replacing its zips and notes"
  gh release upload "$TAG" "${ZIPS[@]}" --clobber
  gh release edit "$TAG" --title "R64texHD $TAG" --notes-file "$NOTES" --draft=false
else
  say "Creating tag + release $TAG (uploading $(du -ch "${ZIPS[@]}" | tail -1 | cut -f1), this takes a while)"
  gh release create "$TAG" "${ZIPS[@]}" --target main --title "R64texHD $TAG" --notes-file "$NOTES" --latest
fi

# ---- 6. check the downloads
say "Checking the download links"
ok=1
for z in "${ZIPS[@]}"; do
  f="$(basename "$z")"; url="https://github.com/$REPO/releases/download/$TAG/$f"
  got="$(curl -sIL -o /dev/null -w '%{http_code} %{size_download}' "$url" | cut -d' ' -f1)"
  printf '  %s  %s\n' "$got" "$f"; [ "$got" = 200 ] || ok=0
done
[ "$ok" = 1 ] || die "some downloads don't work yet (a private repo needs a login: make it public for the in-app downloads)"
say "Published: https://github.com/$REPO/releases/tag/$TAG"
