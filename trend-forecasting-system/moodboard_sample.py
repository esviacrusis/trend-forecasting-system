import os
import io
import base64
from typing import Dict, List

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont


# --------------------------------------------------
# CONFIG
# --------------------------------------------------
MODEL_NAME = "gpt-image-1"
IMAGE_SIZE = "1024x1024"
BOARD_WIDTH = 2200
BOARD_HEIGHT = 2200
MARGIN = 50
CELL_SIZE = 1024
TITLE_Y = 2140

# Create client from environment variable:
# export OPENAI_API_KEY="your_key_here"
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# --------------------------------------------------
# PROMPTS BY COLOR
# --------------------------------------------------
color_prompt_map: Dict[str, Dict[str, List[str]]] = {
    "ivory": {
        "hex": "#FFFFF0",
        "prompts": [
            "Editorial apparel concept inspired by ivory (#FFFFF0), neutral soft palette, womens fashion retail mood board, includes dresses, pants, tops, and accessories, luxury campaign",
            "Apparel flat lay inspired by ivory (#FFFFF0), soft neutral palette, resortwear womens clothing, dresses, pants, tops, accessories, premium styling",
            "Fashion textile and swatch concept inspired by ivory (#FFFFF0), woven fabrics, tonal neutrals, womens apparel design board with dresses, pants, tops",
            "Shoes and handbag styling story inspired by ivory (#FFFFF0), modern womens fashion mood board, clean editorial composition, accessories included",
        ],
    },
    "powder_pink": {
        "hex": "#FADADD",
        "prompts": [
            "Editorial apparel concept inspired by powder pink (#FADADD), soft pastel palette, womens fashion retail mood board, includes dresses, pants, tops, and accessories, luxury campaign",
            "Apparel flat lay inspired by powder pink (#FADADD), pastel palette, resortwear womens clothing, dresses, pants, tops, accessories, premium styling",
            "Fashion textile and swatch concept inspired by powder pink (#FADADD), woven fabrics, tonal pastels, womens apparel design board with dresses, pants, tops",
            "Shoes and handbag styling story inspired by powder pink (#FADADD), modern womens fashion mood board, clean editorial composition, accessories included",
        ],
    },
    "cream": {
        "hex": "#FFFDD0",
        "prompts": [
            "Editorial apparel concept inspired by cream (#FFFDD0), warm neutral palette, womens fashion retail mood board, includes dresses, pants, tops, and accessories, luxury campaign",
            "Apparel flat lay inspired by cream (#FFFDD0), warm neutral palette, resortwear womens clothing, dresses, pants, tops, accessories, premium styling",
            "Fashion textile and swatch concept inspired by cream (#FFFDD0), woven fabrics, tonal neutrals, womens apparel design board with dresses, pants, tops",
            "Shoes and handbag styling story inspired by cream (#FFFDD0), modern womens fashion mood board, clean editorial composition, accessories included",
        ],
    },
}


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def generate_image(prompt: str) -> Image.Image:
    """
    Generate one image from a prompt using OpenAI Images API.
    Returns a PIL Image.
    """
    result = client.images.generate(
        model=MODEL_NAME,
        prompt=prompt,
        size=IMAGE_SIZE,
    )

    b64 = result.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return img


def get_positions() -> List[tuple]:
    """
    Returns 2x2 placement coordinates for the mood board.
    """
    return [
        (MARGIN, MARGIN),
        (MARGIN + CELL_SIZE + MARGIN, MARGIN),
        (MARGIN, MARGIN + CELL_SIZE + MARGIN),
        (MARGIN + CELL_SIZE + MARGIN, MARGIN + CELL_SIZE + MARGIN),
    ]


def draw_title(board: Image.Image, title_text: str) -> None:
    """
    Draw a title at the bottom of the board.
    """
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    draw.text((MARGIN, TITLE_Y), title_text, fill="black", font=font)


def create_mood_board(images: List[Image.Image], title_text: str, output_path: str) -> None:
    """
    Create a 2x2 mood board and save it.
    """
    if len(images) != 4:
        raise ValueError(f"Expected 4 images, got {len(images)}")

    board = Image.new("RGB", (BOARD_WIDTH, BOARD_HEIGHT), "white")
    positions = get_positions()

    for img, pos in zip(images, positions):
        resized = img.resize((CELL_SIZE, CELL_SIZE))
        board.paste(resized, pos)

    draw_title(board, title_text)
    board.save(output_path)
    print(f"Saved: {output_path}")


def slugify(name: str) -> str:
    return name.lower().replace(" ", "_")


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main() -> None:
    for color_name, payload in color_prompt_map.items():
        hex_code = payload["hex"]
        prompts = payload["prompts"]

        print(f"\nGenerating images for {color_name} ({hex_code})...")

        images = []
        for i, prompt in enumerate(prompts, start=1):
            print(f"  Generating image {i}/4...")
            img = generate_image(prompt)
            images.append(img)

        title = f"Apparel Mood Board | {color_name.replace('_', ' ').title()} | {hex_code}"
        output_file = f"{slugify(color_name)}_moodboard.png"

        create_mood_board(images, title, output_file)

    print("\nAll mood boards generated successfully.")


if __name__ == "__main__":
    main()
