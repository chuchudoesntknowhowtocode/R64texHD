@echo off
rem R64texHD: publish a release (runs build\release.sh in bash: Git Bash or WSL). Usage: build\release.cmd [handoff branch]
cd /d "%~dp0.."
bash build/release.sh %*
pause
