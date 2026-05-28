"""批量处理器 v2 — 自动择优 + 质量评分"""
import os, io, time, requests
import numpy as np
from PIL import Image

def _to_native(val):
    """将 numpy 类型转为 Python 原生类型"""
    if isinstance(val, np.generic):
        return val.item()
    return val

def score_image(img):
    """多维度质量评分：清晰度 + 色彩丰富度 + 对比度 + 曝光度
    返回 0-100 的综合评分
    """
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    
    gray = np.mean(arr, axis=2).astype(np.uint8)
    lap = _laplacian_var(gray)
    sharpness = min(lap / 20, 1.0) * 30
    
    std_rgb = np.mean([np.std(arr[:,:,c]) for c in range(3)])
    color_score = min(std_rgb / 60, 1.0) * 25
    
    min_g, max_g = np.min(gray), np.max(gray)
    contrast = min((max_g - min_g) / 200, 1.0) * 25
    
    mean_g = np.mean(gray)
    exposure = 20 - abs(mean_g - 127) * 0.12
    exposure = max(0, min(20, exposure))
    
    total = round(float(sharpness + color_score + contrast + exposure), 1)
    detail = {k: round(float(v), 1) for k, v in {
        "sharpness": sharpness, "color": color_score,
        "contrast": contrast, "exposure": exposure,
    }.items()}
    
    return total, detail


def _laplacian_var(gray_np):
    """纯NumPy拉普拉斯方差"""
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    padded = np.pad(gray_np.astype(np.float32), 1, mode="reflect")
    result = np.zeros_like(gray_np, dtype=np.float32)
    for i in range(gray_np.shape[0]):
        for j in range(gray_np.shape[1]):
            result[i, j] = np.sum(kernel * padded[i:i+3, j:j+3])
    return float(np.var(result))


def select_best(images_with_scores, top_n=1):
    """从多张图中选择评分最高的"""
    sorted_imgs = sorted(images_with_scores, key=lambda x: x[1], reverse=True)
    return sorted_imgs[:top_n]
