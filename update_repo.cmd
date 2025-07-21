@echo off
:: Update Git repository from within the repo folder

:: Go to the script's directory
cd /d %~dp0

echo Updating Git repository in: %cd%

:: Check if this is a Git repository
if not exist ".git" (
    echo.
    echo ERROR: This is not a Git repository.
    echo Make sure the script is inside a valid Git working directory.
    goto fail
)

:: Fetch and pull latest changes
git pull origin main

:: Check if pull failed (e.g., merge conflict, network issue, etc.)
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Git pull failed. Resolve any issues and try again.
    goto fail
)

echo.
echo Repository updated successfully!
goto end

:fail
echo Operation completed with errors.

:end
pause
