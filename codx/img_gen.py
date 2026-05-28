#!/usr/bin/env python3
"""夜不悔 图片工具箱 CLI v3 — 批量 / 变体 / 自动择优 / 质量分层"""
import sys, os, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from img_tool import (
    generate, batch_generate, generate_best, generate_variants,
    upscale_hd, upscale_hq, upscale_4x,
    enhance_prompt, apply_style, build_negative_prompt, detect_scene, score_image,
)

IMG_DIR = Path(__file__).parent / "generated_images"
IMG_DIR.mkdir(parents=True, exist_ok=True)


def _save(img, prompt, args, score=None):
    """保存图片并打印markdown引用"""
    short = "".join(c for c in prompt[:40] if c.isalnum() or c in " _-").strip() or "image"
    fname = args.out or f"{short}_{int(time.time())}.jpg"
    out = IMG_DIR / fname if not Path(fname).is_absolute() else Path(fname)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=95)
    
    kb = os.path.getsize(out) // 1024
    line = f"  {img.size[0]}x{img.size[1]}  {kb}KB  -> {out.resolve()}"
    if score is not None:
        line += f"  [评分: {score}]"
    print(line)
    print(f"\n  ![img](file:///{out.resolve().as_posix()})")
    return out


# ====== 命令实现 ======

def cmd_generate(args):
    """单张生成（增强版）"""
    prompt = " ".join(args.prompt)
    if args.best:
        img, score, detail, seed = generate_best(
            prompt, count=args.best, target_w=args.width, target_h=args.height,
            model="flux" if args.flux else "turbo",
            tier=args.tier or "high", style=args.style,
        )
        _save(img, prompt, args, score)
        print(f"  最优种子: {seed}  详细评分: {detail}")
    else:
        img = generate(prompt, args.width, args.height, args.seed,
                      model="flux" if args.flux else "turbo",
                      tier=args.tier or "high", style=args.style)
        s, d = score_image(img)
        _save(img, prompt, args, s)
        print(f"  评分明细: {d}")


def cmd_batch(args):
    """批量生成"""
    prompt = " ".join(args.prompt)
    results = batch_generate(prompt, count=args.count or 3,
                            target_w=args.width, target_h=args.height,
                            model="flux" if args.flux else "turbo",
                            tier=args.tier or "high", style=args.style)
    # 保存所有结果
    for i, (img, score, detail, seed) in enumerate(results):
        asave = argparse.Namespace(out=args.out, width=args.width, height=args.height)
        asave.out = None  # 用自动命名
        out = _save(img, f"{prompt[:20]}_batch{i+1}", asave, score)
        # 如果是最优，额外标注
        if i == 0:
            print(f"  ★ 最优: {out.name} ({score}分)")


def cmd_variate(args):
    """变体生成"""
    prompt = " ".join(args.prompt)
    results = generate_variants(prompt, variant_count=args.count or 3,
                               target_w=args.width, target_h=args.height,
                               model="flux" if args.flux else "turbo",
                               tier=args.tier or "high", style=args.style)
    for i, (img, score, detail, vidx, mod) in enumerate(results):
        asave = argparse.Namespace(out=args.out, width=args.width, height=args.height)
        asave.out = None
        out = _save(img, f"variant{vidx+1}_{prompt[:15]}", asave, score)
        if i == 0:
            print(f"  ★ 最佳变体: #{vidx+1} ({score}分)")


def cmd_prompt(args):
    """提示词预览"""
    p = " ".join(args.prompt)
    enhanced, scene = enhance_prompt(p, style=args.style, tier=args.tier or "high")
    neg = build_negative_prompt(p, tier=args.tier or "high")
    print(f"\n  原始: {p}")
    print(f"  场景: {scene}")
    print(f"  优化: {enhanced}")
    print(f"  负面: {neg}")


def cmd_upscale(args):
    """对已有图片做高清放大"""
    from PIL import Image
    img = Image.open(args.input)
    w, h = img.size
    if args.factor:
        tw, th = int(w * args.factor), int(h * args.factor)
    elif args.resize:
        parts = args.resize.split("x")
        tw, th = int(parts[0]), int(parts[1])
    else:
        tw, th = w * 2, h * 2
    print(f"  {w}x{h} → {tw}x{th}")
    up = upscale_hd(img, tw, th)
    _save(up, Path(args.input).stem + "_hd", args)


def cmd_list(args):
    """列出最近生成的图片"""
    print(f"\n  {'时间':<14} {'大小':>6}  {'文件名'}")
    print(f"  {'-'*14} {'-'*6}  {'-'*30}")
    for f in sorted(IMG_DIR.glob("*"), key=os.path.getmtime, reverse=True)[:30]:
        s = os.stat(f)
        t = time.strftime("%m-%d %H:%M", time.localtime(s.st_mtime))
        sz = s.st_size // 1024
        print(f"  {t}  {sz:>4}KB  {f.name}")


# ====== 入口 ======

if __name__ == "__main__":
    import argparse
    
    p = argparse.ArgumentParser(description="夜不悔 图片工具 v3", formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  img_gen.py generate "sunset beach" --enhance -o sunset.jpg
  img_gen.py generate "mountain lake" --flux --tier ultra -o alpine.jpg
  img_gen.py generate "cyberpunk city" --best 5 --tier high -o best.jpg
  img_gen.py batch "portrait woman" -n 4 --flux --tier ultra
  img_gen.py variate "dragon fantasy" -n 3 --tier high
  img_gen.py prompt "cute cat" --style photo --tier ultra
  img_gen.py upscale input.jpg --factor 3 -o hd.jpg
  img_gen.py list
""")
    
    sub = p.add_subparsers(dest="cmd")
    
    # generate
    g = sub.add_parser("generate", help="单张生成（支持自动择优）")
    g.add_argument("prompt", nargs="+", help="图片描述")
    g.add_argument("-o", "--out", help="输出文件名")
    g.add_argument("-w", "--width", type=int, default=1536, help="宽度")
    g.add_argument("-H", "--height", type=int, default=1024, help="高度")
    g.add_argument("-s", "--seed", type=int, help="随机种子")
    g.add_argument("--flux", action="store_true", help="使用flux模型（更高质量）")
    g.add_argument("--style", help="风格: photo/painting/sketch/cyberpunk/fantasy/anime...")
    g.add_argument("--tier", choices=["standard","high","ultra"], help="质量等级")
    g.add_argument("--best", type=int, metavar="N", help="自动生成N张择优")
    
    # batch
    b = sub.add_parser("batch", help="批量生成+自动评分排序")
    b.add_argument("prompt", nargs="+")
    b.add_argument("-n", "--count", type=int, default=3, help="生成数量")
    b.add_argument("-w", "--width", type=int, default=1536)
    b.add_argument("-H", "--height", type=int, default=1024)
    b.add_argument("--flux", action="store_true")
    b.add_argument("--style")
    b.add_argument("--tier", choices=["standard","high","ultra"])
    b.add_argument("-o", "--out")
    
    # variate
    v = sub.add_parser("variate", help="基于提示词生成多个变体（角度/构图/光照微调）")
    v.add_argument("prompt", nargs="+")
    v.add_argument("-n", "--count", type=int, default=3, help="变体数量")
    v.add_argument("-w", "--width", type=int, default=1536)
    v.add_argument("-H", "--height", type=int, default=1024)
    v.add_argument("--flux", action="store_true")
    v.add_argument("--style")
    v.add_argument("--tier", choices=["standard","high","ultra"])
    v.add_argument("-o", "--out")
    
    # prompt
    r = sub.add_parser("prompt", help="预览优化后的提示词")
    r.add_argument("prompt", nargs="+")
    r.add_argument("--style")
    r.add_argument("--tier", choices=["standard","high","ultra"])
    
    # upscale
    u = sub.add_parser("upscale", help="对已有图片做高清放大")
    u.add_argument("input", help="输入图片路径")
    u.add_argument("-f", "--factor", type=float, help="放大倍数（如2, 3, 4）")
    u.add_argument("-r", "--resize", help="目标尺寸 如 3840x2560")
    u.add_argument("-o", "--out")
    
    # list
    sub.add_parser("list", help="列出最近生成的图片")
    
    args = p.parse_args()
    
    if args.cmd == "generate": cmd_generate(args)
    elif args.cmd == "batch": cmd_batch(args)
    elif args.cmd == "variate": cmd_variate(args)
    elif args.cmd == "prompt": cmd_prompt(args)
    elif args.cmd == "upscale": cmd_upscale(args)
    elif args.cmd == "list": cmd_list(args)
    else: p.print_help()
