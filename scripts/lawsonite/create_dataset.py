from datetime import datetime
from pathlib import Path
from PIL import Image
import json

root_dir = Path("/db")

icons_dir = root_dir / Path("docs/items-icons")

descriptors = json.load(open(root_dir / Path("docs/items-complete.json"), "r"))

inclusions = {}
exclusions = {}

for k, v in descriptors.items():
    if v["quest_item"] is True:
        exclusions[k] = v
    elif v["incomplete"] is True:
        exclusions[k] = v
    elif v["duplicate"] is True:
        exclusions[k] = v
    elif v["release_date"] is None:
        exclusions[k] = v
    elif datetime.fromisoformat(v["release_date"]) > datetime.fromisoformat(
        "2007-08-31"
    ):
        exclusions[k] = v
    else:
        inclusions[k] = v

print(
    f"Total Descriptors: {len(descriptors)}\nExcluded: {len(exclusions)}\nIncluded: {len(inclusions)}"
)


# with Image.open(icons_dir / "4151.png") as im:
#     im2 = Image.new(im.mode, size=(im.width * 4, im.height), color=(0, 0, 0, 0))
#     rgba = [im.getchannel(channel) for channel in "RGBA"]
#     for chan, xoff in zip(rgba, (im.width * x for x in range(0, 4))):
#         im2.paste(chan, (xoff, 0))
#
#     im2.show()
