"""Dev tool (clean room): preview sheet of every briefed sprite.  python -m games.banjotooie.facesheet <spec> <out.png>"""
import gzip
import json
import os
import sys

from PIL import Image

from games.banjotooie import faces


def main(argv):
    facts = json.load(gzip.open(os.path.join(argv[1], "textures.json.gz"), "rt"))
    uids = sorted(set(faces.EYES) | set(faces.TEXT))
    S = Image.new("RGBA", (20 * 100, ((len(uids) + 19) // 20) * 100), (90, 90, 110, 255))
    for i, u in enumerate(uids):
        k = f"s{u:x}.0"
        if k not in facts:
            print("missing", k)
            continue
        im = Image.fromarray(faces.paint(u, k, facts[k]), "RGBA")
        s = 96 / max(im.size)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.NEAREST)
        S.alpha_composite(im, ((i % 20) * 100, (i // 20) * 100))
    S.convert("RGB").save(argv[2])
    print(len(uids), "briefs ->", argv[2])


if __name__ == "__main__":
    main(sys.argv)
