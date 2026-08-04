from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from PIL.Image import Image

DataGrid = list[list[bool]]


def load_image(i: bytes):
    from io import BytesIO

    try:
        from PIL import Image
    except ImportError as e:
        raise e
    return Image.open(BytesIO(i))


def calculate_row_boundaries(scores: list[int], length: int, detection_threshold: int = 20):
    max_score = max(scores) if scores else 0
    thresh = max_score * (detection_threshold / 100)
    positions = [i + 1 for i, v in enumerate(scores) if v > thresh]
    return [0, *positions, length]


def create_datagrid(img: "Image", detection_threshold: int = 20, white_threshold: int = 127) -> DataGrid:
    img = img.convert("L")
    width, height = img.size

    vertical_scores = [0] * (width - 1)
    for y in range(height):
        previous = img.getpixel((0, y)) > white_threshold  # type: ignore
        for x in range(1, width):
            i = img.getpixel((x, y)) > white_threshold  # type: ignore
            if i != previous:
                vertical_scores[x - 1] += 1
            previous = i

    horizontal_scores = [0] * (height - 1)
    for x in range(width):
        previous = img.getpixel((x, 0)) > white_threshold  # type: ignore
        for y in range(1, height):
            i = img.getpixel((x, y)) > white_threshold  # type: ignore
            if i != previous:
                horizontal_scores[y - 1] += 1
            previous = i

    vertical_edges = calculate_row_boundaries(vertical_scores, width, detection_threshold)
    horizontal_edges = calculate_row_boundaries(horizontal_scores, height, detection_threshold)

    out = []
    for r in range(len(horizontal_edges) - 1):
        y0, y1 = horizontal_edges[r], horizontal_edges[r + 1]
        res = []
        for c in range(len(vertical_edges) - 1):
            x0, x1 = vertical_edges[c], vertical_edges[c + 1]
            whites = 0
            total = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    total += 1
                    if img.getpixel((x, y)) > white_threshold:  # type: ignore
                        whites += 1
            res.append(whites * 2 > total)
        out.append(res)

    if not (all(out[-1]) and all(out[0])):
        out = add_white_edge(out)

    return out


def add_white_edge(data: DataGrid) -> DataGrid:
    data = data.copy()
    for y in range(len(data)):
        data[y].insert(0, True)
        data[y].append(True)
    width = len(data[0])
    data.insert(0, [True] * width)
    data.append([True] * width)
    return data
