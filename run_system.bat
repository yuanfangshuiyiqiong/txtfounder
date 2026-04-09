@echo off
REM FAISS向量数据库系统运行脚本
chcp.com 65001 > nul

echo ========================================
echo FAISS向量数据库操作手册搜索系统
echo ========================================

REM 设置环境变量
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set HF_ENDPOINT=https://hf-mirror.com
set HF_HUB_DISABLE_SYMLINKS_WARNING=1

echo.
echo 可用模式：
echo   1. 构建索引（build）
echo   2. 交互搜索（interactive）
echo   3. 命令行搜索（search）
echo.

set /p mode="请选择模式 (1/2/3): "

if "%mode%"=="1" (
    echo.
    echo 开始构建索引...
    python -X utf8 main.py --mode build
    goto :end
)

if "%mode%"=="2" (
    echo.
    echo 进入交互式搜索模式...
    echo 输入 'quit' 或 'exit' 退出
    echo.
    python -X utf8 main.py --mode interactive
    goto :end
)

if "%mode%"=="3" (
    echo.
    set /p query="请输入搜索查询: "
    if "%query%"=="" (
        echo 查询不能为空
        pause
        exit /b 1
    )
    echo.
    echo 搜索查询: "%query%"
    python -X utf8 main.py --mode search --query "%query%"
    goto :end
)

echo 无效的选择
pause
exit /b 1

:end
echo.
echo 按任意键退出...
pause > nul