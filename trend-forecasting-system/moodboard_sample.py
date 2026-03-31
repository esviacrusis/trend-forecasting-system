from openai import OpenAI
from PIL import Image, ImageDraw
import io
import base64


######

#from openai import OpenAI

#client = OpenAI(
#  api_key="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"
#)

#response = client.responses.create(
#  model="gpt-5-nano",
#  input="write a haiku about ai",
#  store=True,
#)
#
#print(response.output_text);

######






client = OpenAI(
   api_key="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"
) 

hex_color = "#C96F4A"
prompts = [
    f"Editorial apparel concept inspired by {hex_color}, terracotta palette, linen dress, luxury fashion campaign",
    f"Apparel flat lay inspired by {hex_color}, warm earthy palette, resortwear, accessories, premium styling",
    f"Fashion textile and swatch concept inspired by {hex_color}, woven fabrics, tonal neutrals, apparel design board",
    f"Shoes and handbag styling story inspired by {hex_color}, modern fashion mood board, clean editorial composition",
]

images = []
for prompt in prompts:
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024"
    )
    b64 = result.data[0].b64_json
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    images.append(img)

# simple 2x2 mood board
board = Image.new("RGB", (2200, 2200), "white")
positions = [(50, 50), (1125, 50), (50, 1125), (1125, 1125)]

for img, pos in zip(images, positions):
    img = img.resize((1024, 1024))
    board.paste(img, pos)

draw = ImageDraw.Draw(board)
draw.text((50, 2140), f"Apparel Mood Board | Base Color: {hex_color}", fill="black")

board.save("apparel_moodboard.png")




