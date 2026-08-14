"""Ve nhan vat stick figure net den thuan (kieu clip-art toi gian: dau tron rong,
than oval rong, tay chan que) bang PIL - dam bao nhat quan tuyet doi giua cac
bieu cam. Moi nhan vat co 1 chi tiet mau nho (ca vat) de phan biet tren video.
"""

from PIL import Image, ImageDraw

from modules.config import CONFIG, ASSETS_DIR

CANVAS_SIZE = (500, 700)
HEAD_CENTER = (250, 165)
HEAD_RADIUS = 95
NECK_Y = HEAD_CENTER[1] + HEAD_RADIUS
TORSO_BOX = (195, NECK_Y + 5, 305, NECK_Y + 220)  # x0, y0, x1, y1
SHOULDER_L = (TORSO_BOX[0] + 15, TORSO_BOX[1] + 25)
SHOULDER_R = (TORSO_BOX[2] - 15, TORSO_BOX[1] + 25)
HAND_L = (110, 400)
HAND_R = (390, 400)
HIP_L = (222, TORSO_BOX[3] - 10)
HIP_R = (278, TORSO_BOX[3] - 10)
FOOT_L = (195, 640)
FOOT_R = (300, 640)

OUTLINE = "#111111"
LINE_W = 6
EXPRESSIONS = ["neutral", "talking", "happy", "surprised", "angry"]


def _limb(draw, p1, p2, tip_r=14):
    draw.line([p1, p2], fill=OUTLINE, width=LINE_W)
    draw.ellipse([p2[0] - tip_r, p2[1] - tip_r, p2[0] + tip_r, p2[1] + tip_r],
                 outline=OUTLINE, width=LINE_W, fill="#FFFFFF")


def _draw_body(draw: ImageDraw.ImageDraw, accent_color: str):
    _limb(draw, HIP_L, FOOT_L)
    _limb(draw, HIP_R, FOOT_R)
    _limb(draw, SHOULDER_L, HAND_L)
    _limb(draw, SHOULDER_R, HAND_R)

    draw.rounded_rectangle(TORSO_BOX, radius=60, outline=OUTLINE, width=LINE_W, fill="#FFFFFF")

    # Ca vat nho de phan biet nhan vat (chi tiet mau duy nhat)
    cx = (TORSO_BOX[0] + TORSO_BOX[2]) // 2
    ty = TORSO_BOX[1]
    draw.polygon([(cx - 16, ty + 5), (cx + 16, ty + 5), (cx, ty + 55)], fill=accent_color, outline=OUTLINE)


def _draw_head(draw: ImageDraw.ImageDraw):
    x, y = HEAD_CENTER
    r = HEAD_RADIUS
    draw.ellipse([x - r, y - r, x + r, y + r], outline=OUTLINE, width=LINE_W, fill="#FFFFFF")


def _draw_face(draw: ImageDraw.ImageDraw, expression: str):
    x, y = HEAD_CENTER
    eye_dx = 36
    eye_y = y - 8
    eye_r = 6

    brow_up = expression == "surprised"
    brow_angry = expression == "angry"
    brow_happy = expression == "happy"

    for side in (-1, 1):
        cx = x + side * eye_dx
        draw.ellipse([cx - eye_r, eye_y - eye_r, cx + eye_r, eye_y + eye_r], fill=OUTLINE)

        brow_y = eye_y - 22
        if brow_angry:
            draw.line([cx - 14 * side, brow_y + (8 if side < 0 else -6),
                       cx + 14 * side, brow_y + (-6 if side < 0 else 8)], fill=OUTLINE, width=5)
        elif brow_up:
            draw.arc([cx - 15, brow_y - 8, cx + 15, brow_y + 12], start=180, end=360, fill=OUTLINE, width=5)
        elif brow_happy:
            draw.arc([cx - 15, brow_y - 4, cx + 15, brow_y + 12], start=180, end=360, fill=OUTLINE, width=5)
        else:
            draw.line([cx - 14, brow_y, cx + 14, brow_y], fill=OUTLINE, width=5)

    mouth_y = y + 40
    if expression == "neutral":
        draw.line([x - 20, mouth_y, x + 20, mouth_y], fill=OUTLINE, width=5)
    elif expression == "talking":
        draw.ellipse([x - 16, mouth_y - 14, x + 16, mouth_y + 14], outline=OUTLINE, width=5, fill="#FFFFFF")
    elif expression == "happy":
        draw.arc([x - 28, mouth_y - 20, x + 28, mouth_y + 18], start=10, end=170, fill=OUTLINE, width=6)
    elif expression == "surprised":
        draw.ellipse([x - 14, mouth_y - 14, x + 14, mouth_y + 14], outline=OUTLINE, width=5, fill="#FFFFFF")
    elif expression == "angry":
        draw.arc([x - 26, mouth_y - 5, x + 26, mouth_y + 30], start=200, end=340, fill=OUTLINE, width=6)


def generate_character_image(color: str, expression: str) -> Image.Image:
    img = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_body(draw, color)
    _draw_head(draw)
    _draw_face(draw, expression)
    return img


def generate_all_characters(characters: list[dict] | None = None) -> dict:
    characters = characters or CONFIG["characters"]
    out_paths = {}
    for char in characters:
        char_dir = ASSETS_DIR / "characters" / char["name"]
        char_dir.mkdir(parents=True, exist_ok=True)
        out_paths[char["name"]] = {}
        for expression in EXPRESSIONS:
            img = generate_character_image(char["color"], expression)
            path = char_dir / f"{expression}.png"
            img.save(path)
            out_paths[char["name"]][expression] = str(path)
    return out_paths
