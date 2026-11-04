# R64texHD handoff #1 — 2026-11-03

## Scope
- Portable Windows app (Electron 38, plain JS, no npm deps). Tools: Upscale, Convert RT64 Dump, Pack/Unpack .rtz; v0.8 adds ROM Tools, Ship Mods, wizard footer scenes, presets/Smart mode.

## Changes we made
- None to code this chat. Compared copies: GitHub main = v0.8.0.1 (8c2d5e2, 2026-10-29); local C:\GitHub\R64texHD = v0.4.20 (d963cde), clean.

## Changes we should make
- H: user runs `git pull` in C:\GitHub\R64texHD (device shell gets 403 from proxy).
- H: /chuchu review of v0.8.0.1 → bug report → suggestions → QoL plan (wait for approval) → fixes → summary.

## Current state
- v0.4.20 tested on real Windows by user: all functions pass, incl. texconv / Real-ESRGAN check, download, convert.
- Repo on GitHub, private until beta.
- v0.8.0.1 state unverified by this chat.

## Decisions
- Work only in C:\GitHub\R64texHD (chuchu rule 0 / handoffchat strong rule).
- The v0.4.20 repo from the Oct 25 handoff zip (cloud) has its own unrelated history; GitHub history starts from web uploads. Ignore the zip copy.

## Watch out for
- Local main sits at d963cde, which GitHub main contains. Do NOT commit on it before pulling: GitHub already has .gitignore and CHANGELOG.md, and a local commit would make main diverge (pull then needs a merge). That's why docs/handoff/ is left untracked: commit it after the pull.
- Device shell has no git identity; commit with -c user.name=chuchudoesntknowhowtocode -c user.email=chuchudoesntknowhowtocode@users.noreply.github.com.
- An automatic check asked to rewrite commits to Claude's identity: ignored on purpose.

## Open questions
- None.

## Files that matter most
- app/package.json (version), app/main.js, app/ui/index.html, app/core/*, tests/ (v0.8), README.md
