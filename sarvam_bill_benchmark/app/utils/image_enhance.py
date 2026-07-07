"""
Conservative image enhancement for low-quality bill photos.

Design principle: GENTLE enhancements that improve OCR readability
without altering or degrading clean documents. Every operation uses
mild parameters specifically calibrated for document/text images.
"""
import os
import tempfile
from typing import Optional
from app.utils.logging_config import logger

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow is not installed. Image enhancement will be disabled.")


def is_image_file(file_path: str) -> bool:
    """Returns True if the file extension is a supported image format."""
    ext = os.path.splitext(file_path)[1].lower()
    return ext in {".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"}


def enhance_image_for_ocr(file_path: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    Applies gentle, document-safe image enhancements to improve OCR quality.

    Strategy (in order):
      1. Auto-orient using EXIF data (fixes rotated phone photos)
      2. Convert to RGB if needed (handles RGBA/palette modes)
      3. Gentle contrast boost via adaptive equalization (CLAHE-like)
      4. Light sharpening via UnsharpMask with conservative parameters
      5. Mild brightness/contrast normalization

    All parameters are intentionally mild to avoid:
      - Destroying thin text strokes
      - Creating halos around characters
      - Over-saturating colors that confuse OCR
      - Inverting or clipping important pixel data

    Args:
        file_path: Path to the input image file.
        output_dir: Optional directory to save the enhanced image.
                    If None, uses a temp directory.

    Returns:
        Path to the enhanced image file, or None if enhancement fails/skipped.
    """
    if not PILLOW_AVAILABLE:
        logger.warning("Pillow not available, skipping image enhancement.")
        return None

    if not is_image_file(file_path):
        return None

    try:
        img = Image.open(file_path)
        logger.info(f"Image enhancement: Loaded '{os.path.basename(file_path)}' "
                     f"(size={img.size}, mode={img.mode})")

        # Step 1: Auto-orient from EXIF (fixes phone camera rotation)
        img = ImageOps.exif_transpose(img)

        # Step 2: Ensure RGB mode for consistent processing
        if img.mode == "RGBA":
            # Paste onto white background to avoid black artifacts
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Step 3: Gentle auto-contrast
        # cutoff=1 means only clip the extreme 1% of lightest/darkest pixels
        # This normalizes lighting without destroying mid-tone information
        img = ImageOps.autocontrast(img, cutoff=1)

        # Step 4: Mild contrast enhancement
        # Factor 1.15 = 15% contrast boost (very gentle)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.15)

        # Step 5: Light sharpening with UnsharpMask
        # radius=1.5: small blur radius (only sharpens fine details like text)
        # percent=80: mild sharpening strength (much less than default 150)
        # threshold=3: ignores noise by only sharpening edges with >3 level difference
        img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=80, threshold=3))

        # Save enhanced image
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="sarvam_enhance_")

        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        enhanced_path = os.path.join(output_dir, f"{base_name}_enhanced.png")

        # Save as PNG (lossless) to avoid additional JPEG compression artifacts
        img.save(enhanced_path, format="PNG", optimize=True)

        logger.info(f"Image enhancement: Saved enhanced image to '{enhanced_path}'")
        return enhanced_path

    except Exception as e:
        logger.warning(f"Image enhancement failed for '{file_path}': {e}")
        return None
