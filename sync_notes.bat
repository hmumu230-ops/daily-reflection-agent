@echo off
chcp 65001 >nul
setlocal

:: ========================================
:: 每日笔记自动同步脚本
:: 把桌面「每日笔记」文件夹的内容同步到 GitHub
:: 双击运行即可，也可以设为开机自启
:: ========================================

set NOTES_FOLDER=%USERPROFILE%\Desktop\每日笔记
set REPO_DIR=%USERPROFILE%\Desktop\每日反思智能体
set NOTES_REPO_DIR=%REPO_DIR%\notes

:: 获取今天日期 YYYY-MM-DD
for /f "tokens=1-3 delims=-/ " %%a in ('%SystemRoot%\System32\wbem\WMIC.exe os get localdatetime ^| find "."') do (
    set dt=%%a
)
set TODAY=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%

:: 确保桌面笔记文件夹存在
if not exist "%NOTES_FOLDER%" (
    mkdir "%NOTES_FOLDER%"
    echo 已创建文件夹：%NOTES_FOLDER%
    echo 请把今天学到的内容放入这个文件夹，支持 .txt .md .xmind .mm 格式
    echo.
)

:: 确保 notes 目录存在
if not exist "%NOTES_REPO_DIR%" mkdir "%NOTES_REPO_DIR%"

:: 确保今天的子目录存在
if not exist "%NOTES_REPO_DIR%\%TODAY%" mkdir "%NOTES_REPO_DIR%\%TODAY%"

:: 检查桌面笔记文件夹是否有文件
set HAS_FILES=0
for %%f in ("%NOTES_FOLDER%\*.*") do set HAS_FILES=1

if %HAS_FILES%==0 (
    echo [%TODAY%] 桌面笔记文件夹是空的，没有要同步的文件
    echo 把文件放入：%NOTES_FOLDER%
    pause
    exit /b
)

:: 复制文件到 notes/YYYY-MM-DD/
echo [%TODAY%] 正在同步笔记文件...
copy /Y "%NOTES_FOLDER%\*.*" "%NOTES_REPO_DIR%\%TODAY%\" >nul 2>&1
echo [%TODAY%] 文件已复制到 notes\%TODAY%\

:: Git 提交并推送
cd /d "%REPO_DIR%"
git add notes/ >nul 2>&1
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "notes: sync %TODAY% 学习笔记" >nul 2>&1
    echo [%TODAY%] Git 提交成功
    git push origin main >nul 2>&1
    if errorlevel 1 (
        echo [%TODAY%] 推送失败，请检查网络或 Git 配置
    ) else (
        echo [%TODAY%] 已推送到 GitHub
    )
) else (
    echo [%TODAY%] 没有新的变更需要提交
)

echo.
echo 同步完成！你可以在网页上查看笔记和 AI 提炼了。
pause
