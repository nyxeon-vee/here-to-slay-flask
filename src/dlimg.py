# heroes/bad_axe https://www.unstablegameswiki.com/images/b/b7/HtS-Base-034-2E.png
# heroes/bear_claw https://www.unstablegameswiki.com/images/thumb/6/6f/HtS-Base-033-2E.png/300px-HtS-Base-033-2E.png

domain: str = "https://www.unstablegameswiki.com"

# This script should look at file images.txt
# every line looks like this: <li><a href="/index.php?title=Here_To_Slay_-_Bad_Axe" title="Here To Slay - Bad Axe">Bad Axe</a></li>
# it should extract the name of the hero; after: Here_To_Slay_-_{Bad_Axe} (the name in curly brackets) save it in to_lower so hero = bad_axe
# then it should requests get {domain}{hfer} (https://www.unstablegameswiki.com/index.php?title=Here_To_Slay_-_Bad_Axe) find this element:
# <img alt="" src="/images/thumb/b/b7/HtS-Base-034-2E.png/200px-HtS-Base-034-2E.png" decoding="async" width="200" height="280" class="thumbimage" srcset="/images/thumb/b/b7/HtS-Base-034-2E.png/300px-HtS-Base-034-2E.png 1.5x, /images/thumb/b/b7/HtS-Base-034-2E.png/400px-HtS-Base-034-2E.png 2x">
# take src=/images/thumb/b/b7/HtS-Base-034-2E.png/200px-HtS-Base-034-2E.png and remove /thumb and whatever is after the last "/" (includng the "/")
# result should be /images/b/b7/HtS-Base-034-2E.png
# then curl https://www.unstablegameswiki.com/images/b/b7/HtS-Base-034-2E.png > /static/img/heroes/{name_of_hero.to_lower}.png
# result: /static/img/heroes/bad_axe.png
# do that for every line in images.txt

import re
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent

REQUEST_DELAY_SECONDS = 1.5

LINE_RE = re.compile(r'href="/index\.php\?title=Here_To_Slay_-_([^"]+)"')
IMG_RE = re.compile(r'<img alt="" src="([^"]+)"')


def main(images_txt: Path, out_dir: Path, limit: int | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    for line in images_txt.read_text().splitlines():
        if limit is not None and processed >= limit:
            break
        match = LINE_RE.search(line)
        if not match:
            continue

        href_name = match.group(1)
        name = href_name.lower()

        page_url = f"{domain}/index.php?title=Here_To_Slay_-_{href_name}"
        resp = requests.get(page_url)
        resp.raise_for_status()

        img_match = IMG_RE.search(resp.text)
        if not img_match:
            print(f"no image found for {name}")
            continue

        src = img_match.group(1)
        src = src.replace("/thumb", "")
        src = src.rsplit("/", 1)[0]

        img_url = f"{domain}{src}"
        img_resp = requests.get(img_url)
        img_resp.raise_for_status()

        out_path = out_dir / f"{name}.png"
        out_path.write_bytes(img_resp.content)
        print(f"saved {out_path}")

        processed += 1
        time.sleep(REQUEST_DELAY_SECONDS)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("images_txt", help="e.g. images_leaders.txt")
    parser.add_argument("out_subdir", help="e.g. leaders, monsters, items, magic")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    main(
        SCRIPT_DIR / args.images_txt,
        SCRIPT_DIR / "static" / "img" / "card" / args.out_subdir,
        args.limit,
    )
