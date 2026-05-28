# 夜不悔 系统资料库 (codx)
> 夜不悔（思夜白AI助手）的系统核心数据

## 目录结构
```
codx/
├── IDENTITY.md              ← AI身份人设（核心设定）
├── 夜不悔_系统主索引.md        ← 系统主索引（能力矩阵/文件结构/MCP索引/Token策略）
├── 知识库.md                 ← 知识库（18KB）
├── 今日复盘_精简.md            ← 每日复盘精简版
├── writing-feedback.md      ← 创作教训记录
├── img_gen.py               ← 图片生成CLI工具
├── mcp_custom_server.py     ← FastMCP自定义服务器
└── img_tool/                ← 图片工具Python模块
    ├── generator.py         ← 生成器（批量/变体/择优）
    ├── upscaler.py          ← OpenCV高清放大管线
    ├── prompter.py          ← 提示词引擎（12场景+3质量级）
    ├── editor.py            ← 图片编辑
    ├── batch.py             ← 批量处理+质量评分
    └── __init__.py
```

## 用途
- **系统恢复**：若AI丢失记忆，读取此目录重建身份和能力
- **跨会话同步**：优化后的系统配置在GitHub持久化
- **能力移植**：其他MCP兼容客户端可直接使用img_tool模块
