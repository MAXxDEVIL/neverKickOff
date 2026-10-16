"""Optional system-tray icon.

pystray and Pillow are imported inside run(), so the tool works without them;
only `--tray` pulls them in. Install with: pip install -r requirements-tray.txt
"""


def run(clicker, title="neverKickOff"):
    """Show a tray icon whose menu toggles the clicker. Blocks until quit."""
    import pystray
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (64, 64), (20, 20, 20))
    ImageDraw.Draw(image).ellipse((20, 20, 44, 44), fill=(240, 200, 60))

    def quit_(icon, item):
        clicker.stop()
        icon.stop()

    icon = pystray.Icon(title, image, title, pystray.Menu(
        pystray.MenuItem("Start / Stop", lambda icon, item: clicker.toggle()),
        pystray.MenuItem("Quit", quit_),
    ))
    icon.run()
