#!/usr/bin/env python3
"""夜不悔 自定义 MCP Server — FastMCP 实现
将 img_tool 图片生成能力封装为标准 MCP Server

使用方式:
  1. 直接启动:  python mcp_custom_server.py
  2. 通过 config.toml 配置:
     [mcp_servers]
     "yebuhui-img" = { command = "python", args = ["mcp_custom_server.py"] }

依赖: fastmcp (已安装于 .venv)
"""

import sys, os, time, json
from pathlib import Path

# 添加系统资料路径
sys.path.insert(0, str(Path(__file__).parent))

from img_tool import (
    generate, batch_generate, generate_best, generate_variants,
    upscale_hd, upscale_hq, upscale_4x,
    enhance_prompt, build_negative_prompt, detect_scene, score_image,
)
from img_tool.editor import crop, resize, filter_img, to_grayscale

try:
    from fastmcp import FastMCP
except ImportError:
    print("请安装 fastmcp: pip install fastmcp")
    sys.exit(1)

# ============================================================
# 创建 MCP Server
# ============================================================
mcp = FastMCP("夜不悔-图片工具", 
              instructions="夜不悔的图片生成与处理工具箱",
              version="1.0.0")

IMG_DIR = Path(__file__).parent / "generated_images"
IMG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 工具1：图片生成
# ============================================================
@mcp.tool()
def generate_image(
    prompt: str,
    width: int = 1536,
    height: int = 1024,
    model: str = "turbo",
    tier: str = "high",
    style: str = None,
    auto_enhance: bool = True,
) -> str:
    """生成一张图片
    Args:
        prompt: 图片描述文字
        width: 宽度 (默认 1536)
        height: 高度 (默认 1024)
        model: 模型 turbo(快速) 或 flux(高质量)
        tier: 质量等级 standard/high/ultra
        style: 风格 photo/painting/sketch/cyberpunk/fantasy/anime...
        auto_enhance: 是否自动优化提示词
    Returns:
        图片保存路径和评分信息
    """
    try:
        if auto_enhance:
            enhanced, scene = enhance_prompt(prompt, style=style, tier=tier)
            actual_prompt = enhanced
        else:
            actual_prompt = prompt
        
        img = generate(actual_prompt, width, height, 
                      model=model, tier=tier, style=style)
        score, detail = score_image(img)
        
        fname = f"mcp_{int(time.time())}.jpg"
        out = IMG_DIR / fname
        img.save(out, "JPEG", quality=95)
        
        return json.dumps({
            "success": True,
            "path": str(out.resolve()),
            "size": f"{width}x{height}",
            "score": score,
            "detail": detail,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# 工具2：批量生成择优
# ============================================================
@mcp.tool()
def generate_best_image(
    prompt: str,
    count: int = 3,
    width: int = 1536,
    height: int = 1024,
    model: str = "turbo",
    tier: str = "high",
) -> str:
    """批量生成多张图片并自动选择最优
    Args:
        prompt: 图片描述
        count: 生成数量 (默认 3)
        width: 宽度
        height: 高度
        model: 模型 turbo/flux
        tier: 质量等级
    Returns:
        最佳图片的路径和评分明细
    """
    try:
        img, score, detail, seed = generate_best(
            prompt, count=count, target_w=width, target_h=height,
            model=model, tier=tier
        )
        fname = f"mcp_best_{int(time.time())}.jpg"
        out = IMG_DIR / fname
        img.save(out, "JPEG", quality=95)
        
        return json.dumps({
            "success": True,
            "path": str(out.resolve()),
            "size": f"{width}x{height}",
            "score": score,
            "seed": seed,
            "detail": detail,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# 工具3：提示词优化预览
# ============================================================
@mcp.tool()
def optimize_prompt(
    prompt: str,
    tier: str = "high",
    style: str = None,
) -> str:
    """优化图片提示词
    Args:
        prompt: 原始提示词
        tier: 质量等级
        style: 风格
    Returns:
        优化后的提示词、检测到的场景和负面提示词
    """
    enhanced, scene = enhance_prompt(prompt, style=style, tier=tier)
    negative = build_negative_prompt(prompt, tier=tier)
    return json.dumps({
        "original": prompt,
        "enhanced": enhanced,
        "scene": scene,
        "negative_prompt": negative,
    }, ensure_ascii=False)


# ============================================================
# 工具4：高清放大
# ============================================================
@mcp.tool()
def upscale_image(
    image_path: str,
    scale: float = 2.0,
) -> str:
    """对已有图片做高清放大
    Args:
        image_path: 图片路径
        scale: 放大倍数 (默认 2x)
    Returns:
        放大后的图片路径
    """
    try:
        from PIL import Image
        img = Image.open(image_path)
        up = upscale_hq(img, scale)
        name = f"upscale_{int(time.time())}.jpg"
        out = IMG_DIR / name
        up.save(out, "JPEG", quality=95)
        return json.dumps({
            "success": True,
            "path": str(out.resolve()),
            "original_size": f"{img.size[0]}x{img.size[1]}",
            "new_size": f"{up.size[0]}x{up.size[1]}",
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# 工具5：生成变体
# ============================================================
@mcp.tool()
def generate_variant_images(
    prompt: str,
    count: int = 3,
    width: int = 1536,
    height: int = 1024,
) -> str:
    """基于提示词生成多个变体（不同角度/构图/光照）
    Args:
        prompt: 原始提示词
        count: 变体数量
        width: 宽度
        height: 高度
    Returns:
        所有变体的路径和评分
    """
    try:
        results = generate_variants(prompt, variant_count=count,
                                   target_w=width, target_h=height)
        variants = []
        for i, (img, score, detail, vidx, mod) in enumerate(results):
            fname = f"variant_{vidx}_{int(time.time())}.jpg"
            out = IMG_DIR / fname
            img.save(out, "JPEG", quality=95)
            variants.append({
                "index": vidx,
                "path": str(out.resolve()),
                "score": score,
                "modifier": mod,
            })
        return json.dumps({"success": True, "variants": variants}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    print("夜不悔 MCP Server 启动中...", file=sys.stderr)
    mcp.run(transport="stdio")
