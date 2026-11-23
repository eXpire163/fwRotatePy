import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "main.py"
SPEC = importlib.util.spec_from_file_location("rotation_main", MODULE_PATH)
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)


def test_met_path_replaces_image_extension(tmp_path: Path) -> None:
    image = tmp_path / "image.tif"
    assert main.met_path_for(image) == tmp_path / "met" / "image.met"


def test_format_angle_normalizes_360(tmp_path: Path) -> None:
    assert main.format_angle(360) == "0"
    assert main.format_angle(-0.2) == "359.8"
    assert main.format_angle(235.2) == "235.2"


def test_20mm_grid_spacing_at_300_dpi() -> None:
    assert abs(main.grid_spacing_pixels(300.0) - 236.22) < 0.01


def test_draw_grid_adds_lines() -> None:
    image = main.Image.new("RGB", (500, 400), "white")
    result = main.draw_grid(image, 300.0, 300.0)
    assert result.size == (500, 400)
    assert result.mode == "RGB"


def test_write_met_file(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    image.touch()

    main.write_met_file(image, 235.2)

    assert main.met_path_for(image).read_text(encoding="utf-8") == (
        "[Nachbearbeitung]\n"
        "Drehwinkel=235.2\n"
        "Processed=0\n"
    )


def test_preview_dimensions_at_30_percent() -> None:
    assert main.preview_dimensions(4000, 3000, 30) == (1200, 900)
    assert main.preview_dimensions(4000, 3000, 200) == (4000, 3000)
