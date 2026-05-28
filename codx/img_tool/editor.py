"""编辑器 - 图片编辑、滤镜、合成"""
from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw, ImageFont
import os

def crop(img, left, top, right, bottom):
    """裁剪"""
    return img.crop((left, top, right, bottom))

def resize(img, width, height, keep_aspect=True):
    """调整尺寸"""
    if keep_aspect:
        img.thumbnail((width, height), Image.LANCZOS)
        return img
    return img.resize((width, height), Image.LANCZOS)

def enhance(img, sharpness=1.0, contrast=1.0, brightness=1.0, color=1.0):
    """批量增强"""
    if sharpness != 1.0:
        img = ImageEnhance.Sharpness(img).enhance(sharpness)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if color != 1.0:
        img = ImageEnhance.Color(img).enhance(color)
    return img

def filter_img(img, filter_type="sharpen"):
    """应用滤镜"""
    filters = {
        "sharpen": ImageFilter.SHARPEN,
        "blur": ImageFilter.BLUR,
        "gaussian_blur": ImageFilter.GaussianBlur(2),
        "edge_enhance": ImageFilter.EDGE_ENHANCE,
        "smooth": ImageFilter.SMOOTH,
        "emboss": ImageFilter.EMBOSS,
        "contour": ImageFilter.CONTOUR,
        "detail": ImageFilter.DETAIL,
    }
    f = filters.get(filter_type)
    if f:
        return img.filter(f)
    raise ValueError(f"Unknown filter: {filter_type}")

def composite(bg, fg, position=(0, 0), opacity=1.0):
    """图片合成"""
    if opacity < 1.0:
        fg = fg.copy()
        fg.putalpha(int(255 * opacity))
    bg = bg.copy()
    bg.paste(fg, position, fg if fg.mode == "RGBA" else None)
    return bg

def add_text(img, text, position=(10, 10), size=24, color=(255, 255, 255)):
    """添加文字 (有水印场景)"""
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except:
        font = ImageFont.load_default()
    draw.text(position, text, fill=color, font=font)
    return img

def to_grayscale(img):
    """转为灰度"""
    return ImageOps.grayscale(img)

def auto_contrast(img, cutoff=5):
    """自动对比度"""
    return ImageOps.autocontrast(img, cutoff)
