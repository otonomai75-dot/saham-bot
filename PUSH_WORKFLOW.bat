@echo off
cd /d "%~dp0"
set LOG=push_log.txt
echo Running... output will be saved to %LOG%
echo.

(
echo ===== DATE =====
date /t
time /t
echo.
echo ===== CURRENT DIR =====
cd
echo.
echo ===== GIT STATUS =====
git status
echo.
echo ===== GIT BRANCH =====
git branch -a
echo.
echo ===== GIT REMOTE =====
git remote -v
echo.
echo ===== ABORT REBASE (if any) =====
git rebase --abort
echo.
echo ===== CHECKOUT MAIN =====
git checkout main
echo.
echo ===== GIT LOG LAST 5 =====
git log --oneline -5
echo.
echo ===== ADD ALL =====
git add -A
echo.
echo ===== COMMIT =====
git commit -m "Update saham-bot with workflow and harga jual feature"
echo.
echo ===== FORCE PUSH =====
git push origin main --force
echo.
echo ===== DONE =====
) > %LOG% 2>&1

echo.
echo Finished! Opening log...
type %LOG%
echo.
echo Log saved at: %CD%\%LOG%
pause
