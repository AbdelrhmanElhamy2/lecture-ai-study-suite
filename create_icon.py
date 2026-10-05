from pathlib import Path
from PIL import Image, ImageDraw

def create_app_icon():
    project_dir = Path(__file__).resolve().parent
    master_path = project_dir / "static" / "biomedical_icon_master.jpg"
    
    if not master_path.exists():
        raise FileNotFoundError(f"Master icon image not found at {master_path}")
        
    img = Image.open(master_path)

    # Inset crop box to align seamlessly with the outer silver bezel
    box = (152, 146, 872, 866)
    cropped = img.crop(box)

    target_size = 512
    resized = cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)

    # Create supersampled squircle mask for smooth antialiased alpha corners
    ss = 4
    mask_hi = Image.new('L', (target_size * ss, target_size * ss), 0)
    m_draw = ImageDraw.Draw(mask_hi)
    m_draw.rounded_rectangle([0, 0, target_size * ss, target_size * ss], radius=120 * ss, fill=255)
    mask = mask_hi.resize((target_size, target_size), Image.Resampling.LANCZOS)

    final = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 0))
    final.paste(resized, (0, 0), mask)

    # Save PNG favicon/app icon
    png_path = project_dir / "static" / "app_icon.png"
    final.save(png_path, format="PNG")
    print(f"Created Web Favicon PNG: {png_path.absolute()}")

    # Save multi-resolution Windows ICO (both filenames for compatibility & cache-busting)
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    ico_path = project_dir / "app_icon.ico"
    final.save(ico_path, format="ICO", sizes=ico_sizes)
    print(f"Created Windows ICO: {ico_path.absolute()}")

    bme_ico_path = project_dir / "biomedical_icon.ico"
    final.save(bme_ico_path, format="ICO", sizes=ico_sizes)
    print(f"Created Windows ICO: {bme_ico_path.absolute()}")

if __name__ == "__main__":
    create_app_icon()
