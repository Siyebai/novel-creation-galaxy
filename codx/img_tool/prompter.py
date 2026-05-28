"""提示词引擎 v3 — 细分场景分类 + 负面提示词注入 + 质量分层"""
import re

# ============================================================
# 1. 细分场景分类
# ============================================================
SCENE_KEYWORDS = {
    "portrait":      ["portrait","face","person","woman","man","people","selfie","模特","人像","头像"],
    "landscape":     ["landscape","mountain","ocean","sea","beach","sunset","sunrise","forest","nature","sky","valley","river","lake","waterfall","荒野","山水","风景"],
    "cityscape":     ["city","urban","street","building","skyline","architecture","downtown","night market","霓虹","城市","街道","建筑"],
    "food":          ["food","dish","cuisine","meal","dessert","cake","coffee","drink","水果","美食","甜品"],
    "animal":        ["animal","cat","dog","bird","horse","wildlife","pet","狼","动物","猫","狗"],
    "indoor":        ["interior","room","indoor","house","office","bedroom","living room","室内"],
    "fantasy":       ["fantasy","magic","dragon","elf","mythical","sci-fi","alien","robot","cyberpunk","dystopian","魔法","科幻","奇幻"],
    "product":       ["product","shoes","bag","watch","car","bottle","商品","产品","广告"],
    "night":         ["night","dark","moon","stars","night sky","夜景","夜晚"],
    "abstract":      ["abstract","geometric","pattern","texture","minimalist","抽象","几何"],
    "documentary":   ["documentary","street photography","candid","纪实","街拍","人文"],
    "aerial":        ["aerial","drone","bird's eye","top view","俯瞰","航拍","鸟瞰"],
}

QUALITY_TAGS = {
    "portrait":    "professional portrait photography, soft natural lighting, shallow depth of field, detailed skin texture, sharp eyes, 8K",
    "landscape":   "breathtaking landscape photography, dramatic golden hour lighting, hyperrealistic, vivid colors, deep depth of field, National Geographic style",
    "cityscape":   "urban landscape photography, sharp architectural details, cinematic lighting, vibrant neon glow, depth, atmosphere",
    "food":        "food photography, mouth-watering, professional lighting, shallow depth of field, vibrant colors, highly detailed texture",
    "animal":      "wildlife photography, sharp fur detail, natural habitat, golden hour lighting, National Geographic quality",
    "indoor":      "interior design photography, natural lighting, elegant composition, warm tones, highly detailed",
    "fantasy":     "fantasy digital art, epic composition, dramatic lighting, intricate details, volumetric effects, ethereal glow, unreal engine 5",
    "product":     "commercial product photography, studio lighting, clean background, sharp focus, high-end, 8K detail",
    "night":       "night photography, long exposure, starry sky, light trails, moody atmosphere, high contrast",
    "abstract":    "abstract art, geometric composition, vibrant colors, high contrast, detailed texture, minimalist",
    "documentary": "street photography, candid moment, documentary style, authentic atmosphere, rich storytelling",
    "aerial":      "aerial photography, drone shot, majestic landscape, wide vista, breathtaking perspective",
}

# ============================================================
# 2. 负面提示词体系 — 按场景针对性去劣
# ============================================================
NEGATIVE_COMMON = "blurry, low quality, distorted, deformed, ugly, bad anatomy, watermark, text, logo, signature, cropped, worst quality, low resolution, jpeg artifacts, messy"

NEGATIVE_SPECIFIC = {
    "portrait":    "double chin, blemishes, asymmetric face, missing limbs, bad hands, bad fingers, extra fingers, mutation",
    "landscape":   "overexposed, underexposed, flat colors, hazy, lens flare, chromatic aberration, overprocessed",
    "cityscape":   "blurry buildings, distorted perspective, misaligned, flat lighting, noise, grain",
    "food":        "unappetizing, burnt, overly processed, artificial colors, melting, deformed shape",
    "animal":      "deformed animal, wrong anatomy, blurry fur, bad proportions, unnatural colors",
    "fantasy":     "amateur, poor composition, generic, boring, flat lighting, low detail, inconsistent style",
    "night":       "overexposed, noise, grain, light pollution, blurry stars, trailing",
    "abstract":    "messy composition, chaotic, unbalanced, noisy, low contrast, muddy colors",
}

def detect_scene(prompt):
    """智能检测场景类型"""
    p_lower = prompt.lower()
    scores = {}
    for scene, keywords in SCENE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in p_lower)
        if score > 0:
            scores[scene] = score
    if not scores:
        return "general"
    return max(scores, key=scores.get)

# ============================================================
# 3. 质量分层系统
# ============================================================
QUALITY_TIERS = {
    "standard": {
        "positive": "high quality, detailed",
        "negative": NEGATIVE_COMMON,
    },
    "high": {
        "positive": "masterpiece, best quality, ultra-detailed, sharp focus, vivid, 8K, award-winning",
        "negative": NEGATIVE_COMMON,
    },
    "ultra": {
        "positive": "masterpiece, best quality, ultra-detailed, intricate details, sharp focus, vivid colors, 8K UHD, HDR, award-winning photograph, professional lighting, cinematic composition, subsurface scattering, ray tracing, volumetric lighting, hyperrealistic, photorealistic, trending on ArtStation",
        "negative": NEGATIVE_COMMON,
    },
}

# ============================================================
# 4. 风格模板
# ============================================================
STYLES = {
    "photo":        "{p}, photorealistic, natural lighting, 8K, DSLR, professional photography",
    "painting":     "{p}, oil painting, canvas texture, artistic, brush strokes, impasto, rich colors",
    "sketch":       "{p}, pencil sketch, black and white, hand-drawn, detailed shading, cross-hatching",
    "cyberpunk":    "{p}, cyberpunk style, neon lights, rain, futuristic city, blade runner aesthetic, neon glow",
    "fantasy":      "{p}, fantasy art, magical glow, ethereal, mystical, intricate details, epic scale",
    "pixel":        "{p}, pixel art, retro game style, 16-bit, crisp pixels, vibrant palette",
    "watercolor":   "{p}, watercolor painting, soft colors, paper texture, flowing pigments, artistic",
    "anime":        "{p}, anime style, cel shading, vibrant, clean lines, detailed background, Studio Ghibli",
    "realistic":    "{p}, hyperrealistic, photograph, highly detailed, 4K, sharp focus, natural lighting",
    "vintage":      "{p}, vintage photography, film grain, warm tones, nostalgic, retro aesthetic, Kodak Portra",
    "minimalist":   "{p}, minimalist composition, clean lines, negative space, simple elegant, muted colors",
    "cinematic":    "{p}, cinematic shot, dramatic lighting, anamorphic lens, film grain, movie still, epic",
    "noir":         "{p}, film noir, high contrast, black and white, dramatic shadows, moody, gritty",
    "sci-fi":       "{p}, sci-fi concept art, futuristic, holographic glow, sleek design, high tech, detailed",
}

# ============================================================
# 5. 变体生成 — seed-aware 微调
# ============================================================
VARIATION_MODIFIERS = [
    "slightly different composition,",       # 构图微调
    "different angle,",                       # 不同角度
    "alternative lighting,",                  # 不同光照
    "tilted perspective, artistic view,",     # 艺术视角
    "close up crop, more detailed,",          # 近景特写
    "wider view, more context,",              # 远景
]

def variation_prompt(original_prompt, variant_idx):
    """基于原始提示词生成变体"""
    modifier = VARIATION_MODIFIERS[variant_idx % len(VARIATION_MODIFIERS)]
    return f"{modifier} {original_prompt}"

# ============================================================
# 6. 主接口函数
# ============================================================

def enhance_prompt(prompt, style=None, tier="high"):
    """全功能提示词增强"""
    p = prompt.strip().rstrip(".,")
    scene = detect_scene(p)
    
    # 应用风格
    if style and style in STYLES:
        p_fmt = STYLES[style].format(p=p)
    else:
        # 根据场景注入质量标签
        q_tag = QUALITY_TAGS.get(scene, QUALITY_TAGS["landscape"])
        tier_tag = QUALITY_TIERS.get(tier, QUALITY_TIERS["high"])["positive"]
        p_fmt = f"{p}, {tier_tag}, {q_tag}"
    
    return p_fmt, scene

def build_negative_prompt(prompt, tier="high"):
    """构建负面提示词"""
    scene = detect_scene(prompt)
    specific = NEGATIVE_SPECIFIC.get(scene, "")
    common = QUALITY_TIERS.get(tier, QUALITY_TIERS["high"])["negative"]
    if specific:
        return f"{common}, {specific}"
    return common

def apply_style(prompt, style):
    """应用特定风格"""
    if style in STYLES:
        return STYLES[style].format(p=prompt.strip().rstrip(".,"))
    return prompt

def generate_variant(original_prompt, idx):
    """生成变体提示词"""
    return variation_prompt(original_prompt, idx)
