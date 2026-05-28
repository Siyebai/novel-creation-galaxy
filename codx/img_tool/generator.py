"""生成器 v3 — 批量生成 + 变体 + 质量评分集成"""
import io, time, requests
from PIL import Image
from .upscaler import upscale_hd, fit_and_upscale
from .prompter import enhance_prompt, build_negative_prompt, generate_variant, detect_scene
from .batch import score_image, select_best

API_BASE = "https://image.pollinations.ai/prompt"
MAX_PIXELS = 768 * 768


def _pollinations(prompt, width, height, seed=None, model="turbo"):
    """调用 Pollinations API"""
    params = {"width": width, "height": height, "model": model}
    if seed is not None:
        params["seed"] = seed
    url = f"{API_BASE}/{requests.utils.quote(prompt)}"
    for k, v in params.items():
        url += f"&{k}={v}"
    
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=180)
            if r.status_code == 200:
                return Image.open(io.BytesIO(r.content))
            elif r.status_code == 402:
                print(f"  [队列满] 等待15s...")
                time.sleep(15)
            else:
                print(f"  [HTTP {r.status_code}] 重试...")
                time.sleep(10)
        except Exception as e:
            print(f"  [错误] {e} 重试...")
            time.sleep(10)
    raise RuntimeError("API 5次重试均失败")


def _calc_native(target_w, target_h):
    """计算API原生分辨率（保持比例，不超过MAX_PIXELS）"""
    aspect = target_w / target_h
    native_h = int((MAX_PIXELS / aspect) ** 0.5)
    native_w = int(native_h * aspect)
    native_w = min(native_w, 768)
    native_h = min(native_h, 768)
    return native_w, native_h


def generate(prompt, target_w=1536, target_h=1024, seed=None, model="turbo",
             tier="high", style=None, negative_prompt=None):
    """单张生成 + 高清放大
    Args:
        prompt: 图片描述
        target_w, target_h: 目标分辨率
        seed: 随机种子
        model: turbo(快) 或 flux(好)
        tier: 质量等级 standard/high/ultra
        style: 风格模板
        negative_prompt: 自定义负面提示词
    Returns:
        PIL.Image
    """
    # 1. 提示词增强
    enhanced, scene = enhance_prompt(prompt, style=style, tier=tier)
    if negative_prompt is None:
        negative_prompt = build_negative_prompt(prompt, tier=tier)
    
    # 2. API原生图
    nw, nh = _calc_native(target_w, target_h)
    print(f"  [{model}] 场景:{scene} 原生:{nw}x{nh} → 目标:{target_w}x{target_h}")
    
    img = _pollinations(enhanced, nw, nh, seed, model)
    
    # 3. 高清放大
    if img.size != (target_w, target_h):
        img = upscale_hd(img, target_w, target_h)
    
    return img


def generate_no_upscale(prompt, width=768, height=512, seed=None, model="turbo",
                        tier="high", style=None):
    """仅生成，不放大"""
    enhanced, _ = enhance_prompt(prompt, style=style, tier=tier)
    return _pollinations(enhanced, width, height, seed, model)


def batch_generate(prompt, count=3, target_w=1536, target_h=1024,
                   model="turbo", tier="high", style=None):
    """批量生成N张 → 自动评分 → 返回所有结果
    Returns:
        [(PIL.Image, score, detail), ...]
    """
    results = []
    print(f"\n  === 批量生成 {count}张 ===")
    
    for i in range(count):
        seed = int(time.time() * 1000) % 100000 + i * 37
        print(f"\n  [{i+1}/{count}] seed={seed}")
        try:
            img = generate(prompt, target_w, target_h, seed=seed,
                          model=model, tier=tier, style=style)
            score, detail = score_image(img)
            print(f"  → 评分: {score} {detail}")
            results.append((img, score, detail, seed))
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    
    # 排序
    results.sort(key=lambda x: x[1], reverse=True)
    print(f"\n  === 最佳: {results[0][1]}分 (seed={results[0][3]}) ===")
    return results


def generate_best(prompt, count=3, target_w=1536, target_h=1024,
                  model="turbo", tier="high", style=None):
    """批量生成N张 → 自动选最优 → 只返回最佳那张"""
    results = batch_generate(prompt, count, target_w, target_h,
                            model, tier, style)
    if not results:
        raise RuntimeError("批量生成全部失败")
    return results[0]  # (img, score, detail, seed)


def generate_variants(prompt, variant_count=3, target_w=1536, target_h=1024,
                      model="turbo", tier="high", style=None):
    """基于原始提示词生成多个变体（角度/构图/光照微调）
    每张用不同种子 + 不同修饰词
    Returns:
        [(PIL.Image, score, detail, variant_idx, modifier), ...]
    """
    results = []
    print(f"\n  === 变体生成 {variant_count}种 ===")
    
    for i in range(variant_count):
        variant_prompt = generate_variant(prompt, i)
        seed = int(time.time() * 1000) % 100000 + i * 71
        print(f"\n  [变体{i+1}/{variant_count}] seed={seed}")
        print(f"    提示词: {variant_prompt[:60]}...")
        try:
            enhanced, _ = enhance_prompt(variant_prompt, style=style, tier=tier)
            nw, nh = _calc_native(target_w, target_h)
            img = _pollinations(enhanced, nw, nh, seed, model)
            img = upscale_hd(img, target_w, target_h)
            score, detail = score_image(img)
            print(f"  → 评分: {score}")
            results.append((img, score, detail, i, variant_prompt[:40]))
        except Exception as e:
            print(f"  ✗ 失败: {e}")
    
    results.sort(key=lambda x: x[1], reverse=True)
    if results:
        print(f"\n  === 最佳变体: #{results[0][3]+1} ({results[0][1]}分) ===")
    return results
