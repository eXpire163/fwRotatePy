# Image Rotation

A Windows desktop tool for assigning rotation angles to TIFF/JPEG images.

## Features

- Select a source image folder at startup
- Live preview with mouse drag: 1 degree per pixel of horizontal movement
- Fine adjustment: Left/Right arrow keys change the angle by 0.2 degrees
- Press Space or click **Save** to write a `.met` file beside the image
- Automatically skips images that already have a `.met` file
- Automatically advances to the next unprocessed image

## Run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src\main.py
```

## `.met` format

For an image named `photo.jpg`, the saved file is `photo.met`:

```ini
[Nachbearbeitung]
Drehwinkel=235.2
Processed=0
```
