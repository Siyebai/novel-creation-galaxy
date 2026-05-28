"""放大器 v4 — 多级渐进放大 + 自适应去模糊 + 智能锐化"""
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageChops

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


def _compute_sharpness(cv_img):
    """计算图像清晰度评分（拉普拉斯方差）"""
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) if len(cv_img.shape) == 3 else cv_img
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def _adaptive_deblur(cv_img, target_sharpness=150):
    """自适应去模糊：如果清晰度不足，应用反卷积锐化"""
    sharpness = _compute_sharpness(cv_img)
    if sharpness >= target_sharpness:
        return cv_img  # 够清晰，跳过
    
    # 多次轻度锐化直到达标
    result = cv_img.copy()
    for _ in range(3):
        kernel = np.array([[-0.3,-0.3,-0.3],
                           [-0.3, 3.4,-0.3],
                           [-0.3,-0.3,-0.3]])
        result = cv2.filter2D(result, -1, kernel)
        curr = _compute_sharpness(result)
        if curr >= target_sharpness:
            break
    
    # 防止过锐导致噪声放大
    result = cv2.bilateralFilter(result, 3, 15, 15)
    return result


def _smart_upscale_stage(cv_img, target_w, target_h):
    """单级智能放大：根据放大倍数选择最优插值算法"""
    h, w = cv_img.shape[:2]
    scale = max(target_w / w, target_h / h)
    
    if scale <= 1.5:
        interp = cv2.INTER_LANCZOS4
    elif scale <= 3.0:
        interp = cv2.INTER_CUBIC
    else:
        interp = cv2.INTER_LINEAR  # 大倍数时线性更稳定
    
    up = cv2.resize(cv_img, (target_w, target_h), interpolation=interp)
    return up


def _multi_stage_upscale(cv_img, target_w, target_h):
    """多级渐进放大：每次最多2x，中间插去模糊和细节增强"""
    h, w = cv_img.shape[:2]
    if w >= target_w and h >= target_h:
        return cv_img
    
    current = cv_img
    stage = 0
    while current.shape[1] < target_w or current.shape[0] < target_h:
        stage += 1
        next_w = min(current.shape[1] * 2, target_w)
        next_h = min(current.shape[0] * 2, target_h)
        
        # 智能放大
        current = _smart_upscale_stage(current, next_w, next_h)
        
        # 每级放大后去模糊
        current = _adaptive_deblur(current, target_sharpness=120 + stage * 20)
        
        # 第2级起做细节增强
        if stage >= 2:
            current = cv2.detailEnhance(current, sigma_s=8, sigma_r=0.12)
    
    return current


def _final_enhance(cv_img):
    """最终画质增强管线：降噪 + 对比度 + 色彩"""
    # 1. 轻度降噪（保护边缘）
    denoised = cv2.fastNlMeansDenoisingColored(cv_img, None, 5, 5, 5, 15)
    
    # 2. 自适应对比度
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    # 3. 最终智能锐化
    result = _adaptive_deblur(result, target_sharpness=200)
    
    return result


def upscale_hd(img, target_w, target_h):
    """高清放大主入口：多级渐进放大 + 最终增强"""
    if not HAS_CV2:
        return img.resize((target_w, target_h), Image.LANCZOS)
    
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    # 1. 多级放大
    up = _multi_stage_upscale(cv_img, target_w, target_h)
    
    # 2. 最终画质增强
    up = _final_enhance(up)
    
    # 3. 确保目标尺寸精确
    if up.shape[1] != target_w or up.shape[0] != target_h:
        up = cv2.resize(up, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    
    return Image.fromarray(cv2.cvtColor(up, cv2.COLOR_BGR2RGB))


def upscale_hq(img, scale_factor=2.0):
    """等比高清放大（指定倍数）"""
    w, h = img.size
    tw, th = int(w * scale_factor), int(h * scale_factor)
    return upscale_hd(img, tw, th)


def upscale_4x(img):
    """4x 超级放大"""
    return upscale_hq(img, 4.0)


def fit_and_upscale(img, target_w, target_h):
    """保持比例放大 + 中心裁切到目标尺寸"""
    w, h = img.size
    ratio = max(target_w / w, target_h / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    up = upscale_hd(img, new_w, new_h)
    left = (up.width - target_w) // 2
    top = (up.height - target_h) // 2
    return up.crop((left, top, left + target_w, top + target_h))
