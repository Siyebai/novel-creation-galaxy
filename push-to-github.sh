#!/bin/bash
# 创世银河引擎 — GitHub 推送脚本
# 仓库: https://github.com/Siyebai/novel-creation-galaxy

cd "$(dirname "$0")"

echo "=== 创世银河引擎 GitHub 推送 ==="
echo "仓库: https://github.com/Siyebai/novel-creation-galaxy"
echo ""

# 检查 remote
if ! git remote get-url origin &>/dev/null; then
    echo "设置 remote..."
    git remote add origin https://github.com/Siyebai/novel-creation-galaxy.git
fi

# 同步最新引擎文件
echo "同步引擎文件..."
cp ~/novels/novel-creation-galaxy-engine.md "./创世银河小说创作工作系统.md"

# 提交并推送
echo "提交变更..."
git add -A
git status --short

if git diff --cached --quiet; then
    echo "没有新的变更。"
else
    git commit -m "chore: sync engine updates
Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
fi

echo "推送到 GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 推送成功！"
    echo "🔗 https://github.com/Siyebai/novel-creation-galaxy"
else
    echo ""
    echo "❌ 推送失败。检查网络连接或 VPN。"
    echo "也可手动推送: cd ~/novels/novel-creation-galaxy && git push -u origin main"
fi
