"""Audit the source editions, image locators and color patches against local PDFs."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
from statistics import median
import sys
import tempfile

DOCS = Path(__file__).resolve().parents[1] / "docs"


def load(name):
    return json.loads((DOCS / name).read_text(encoding="utf-8"))


def pdf_files(inputs):
    """Limit the search to supplied PDFs and their explicitly selected directories."""
    for path in inputs:
        if path.is_file() and path.suffix.lower() == ".pdf":
            yield path
        elif path.is_dir():
            yield from (p for p in path.rglob("*") if p.suffix.lower() == ".pdf" and p.is_file())
        else:
            raise ValueError("Supply a readable PDF or a directory of PDFs.")


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_records(books):
    """Group records by source PDF, so only one book needs to be open at a time."""
    selected = {book["set"]: book["sha256"] for book in books}

    def included(set_number, digest):
        if set_number not in selected:
            return False
        if selected[set_number] != digest:
            raise ValueError(f"Study and corpus disagree on the edition of set {set_number}.")
        return True

    groups = defaultdict(list)
    for study, filename in [
        ("assembly", "research/PERSPECTIVE-DATA.json"),
        ("catalogue", "research/CAMERA-CATALOGUE-DATA.json"),
    ]:
        for record in load(filename)["records"]:
            source = record["source"]
            digest = source.get("pdf_sha256") or source["sha256"]
            if included(source["set"], digest):
                groups[digest].append({
                    "study": study, "page": source["page"],
                    "image": source.get("name") or source["image"],
                    "size": source.get("size") or source["pixels"],
                    "encoded": source.get("encoded_sha256") or source["encoded_image_sha256"],
                    **{k: source[k] for k in ("pixel_sha256", "icc_sha256") if k in source},
                })

    for filename in ("THREE-FACE-SHADING.json", "MATERIAL-TRANSFER.json"):
        data = load(filename)
        for row in data["observations"]:
            if not included(row["set"], row["source_sha256"]):
                continue
            patches = []
            for face, value in row["faces"].items():
                if filename == "THREE-FACE-SHADING.json":
                    box = data["rois_native_pixels_half_open"][face]
                    center = value
                    shifts = row["sensitivity"][face]["shifted_medians"]
                else:
                    box = value["box"]
                    center = value["observed"]
                    shifts = value["shifted"]
                patches.append((face, box, center, shifts))
            groups[row["source_sha256"]].append({
                "study": filename.removesuffix(".json").lower(), "page": row["page"],
                "image": row["image"], "encoded": row["encoded_sha256"],
                "size": row["native_size"], "pixel_sha256": row["decoded_pixel_sha256"],
                "icc_sha256": row["profile_sha256"], "patches": patches,
            })
    return groups


def patch_median(image, box, dx=0, dy=0):
    x0, y0, x1, y1 = box
    bounds = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    if not (0 <= bounds[0] < bounds[2] <= image.width
            and 0 <= bounds[1] < bounds[3] <= image.height):
        raise ValueError("A measurement window falls outside the native image.")
    channels = image.crop(bounds).tobytes()
    return [median(channels[i::3]) for i in range(3)]


def check_image(reader, row):
    if not 1 <= row["page"] <= len(reader.pages):
        raise ValueError("The image locator is outside the PDF.")
    page = reader.pages[row["page"] - 1]
    name = "/" + row["image"].lstrip("/").split(".")[0]
    asset = page.images[name]
    image = asset.image.convert("RGB")
    checks = {
        "encoded image": hashlib.sha256(asset.data).hexdigest() == row["encoded"],
        "native size": list(image.size) == row["size"],
    }
    if "pixel_sha256" in row:
        checks["RGB pixels"] = hashlib.sha256(image.tobytes()).hexdigest() == row["pixel_sha256"]
    if "icc_sha256" in row:
        space = page["/Resources"]["/XObject"][name].get("/ColorSpace")
        space = space.get_object() if space else None
        icc_hash = None
        if isinstance(space, list) and space[0] == "/ICCBased":
            icc_hash = hashlib.sha256(space[1].get_object().get_data()).hexdigest()
        checks["ICC profile"] = icc_hash == row["icc_sha256"]
    for face, box, center, shifts in row.get("patches", []):
        checks[face] = patch_median(image, box) == center
        offsets = {(shift["dx"], shift["dy"]) for shift in shifts}
        checks[face + " window coverage"] = len(shifts) == 9 and offsets == {
            (dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
        }
        checks[face + " shifted windows"] = all(
            patch_median(image, box, shift["dx"], shift["dy"]) == shift["rgb"]
            for shift in shifts
        )
    return [name for name, passes in checks.items() if not passes]


def audit(inputs, books):
    import PIL
    import pypdf

    groups = selected_records(books)
    needed = {book["sha256"] for book in books}
    found = {}
    for path in pdf_files(inputs):
        digest = file_hash(path)
        if digest in needed:
            found[digest] = path
        if len(found) == len(needed):
            break

    results = []
    for book in books:
        digest = book["sha256"]
        result = {"set": book["set"], "sha256": digest, "source": book["source_url"],
                  "status": "missing edition", "records_checked": {}, "failures": []}
        results.append(result)
        if digest not in found:
            continue
        with found[digest].open("rb") as stream:
            reader = pypdf.PdfReader(stream)
            if len(reader.pages) != book["pages"]:
                result["failures"].append("page count")
            if any(not 1 <= page <= len(reader.pages) for page in book["sample_pages"]):
                result["failures"].append("sample page range")
            for row in groups[digest]:
                study = row["study"]
                counts = result["records_checked"]
                counts[study] = counts.get(study, 0) + 1
                try:
                    failed = check_image(reader, row)
                except (KeyError, IndexError, TypeError, ValueError, pypdf.errors.PdfReadError) as error:
                    failed = [f"could not read measurement ({type(error).__name__})"]
                if failed:
                    result["failures"].append({"study": study, "page": row["page"],
                                               "image": row["image"], "checks": failed})
            result["status"] = "failed" if result["failures"] else "verified"
    return {"status": "PASS" if all(r["status"] == "verified" for r in results) else "FAIL",
            "pypdf": pypdf.__version__, "Pillow": PIL.__version__, "books": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, help="PDFs or directories to search recursively")
    parser.add_argument("--set", dest="sets", action="append", help="Limit the audit to a set number (repeatable)")
    parser.add_argument("--list", action="store_true", help="List expected editions and official source links")
    parser.add_argument("--report", type=Path, help="Save JSON to a new file")
    args = parser.parse_args()
    books = load("STYLE-SOURCES.json")["sources"]
    if args.sets:
        unknown = set(args.sets) - {b["set"] for b in books}
        if unknown:
            parser.error("Unknown set number: " + ", ".join(sorted(unknown)))
        books = [b for b in books if b["set"] in args.sets]
    if args.list:
        for book in books:
            print(book["set"], book["sha256"], book["source_url"], sep="\t")
        return 0
    if not args.inputs:
        parser.error("Supply a PDF or directory, or use --list to see the source editions.")
    try:
        report = audit(args.inputs, books)
        if args.report:
            with tempfile.TemporaryDirectory(dir=args.report.parent) as temp:
                staged = Path(temp) / "report.json"
                staged.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                os.link(staged, args.report)
    except ImportError as error:
        parser.exit(2, f"The source audit needs pypdf and Pillow ({error}).\n")
    except (ValueError, OSError) as error:
        parser.exit(2, f"Source audit: {error}\n")
    for book in report["books"]:
        if book["status"] != "verified":
            print(f"{book['set']}: {book['status']} (expected SHA-256 {book['sha256']})")
            for failure in book["failures"]:
                print(" ", failure)
    verified = sum(row["status"] == "verified" for row in report["books"])
    print(f"{report['status']}: {verified}/{len(books)} source editions verified.")
    return int(report["status"] != "PASS")


if __name__ == "__main__":
    sys.exit(main())
