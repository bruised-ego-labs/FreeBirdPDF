# freebird/constants.py
import os

# Resource paths - work on both Windows and Unix systems
RESOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources")
BACKGROUND_IMAGE_PATH = os.path.join(RESOURCES_DIR, "FreeBird.png")
ICON_PATH = os.path.join(RESOURCES_DIR, "pdf_icon.png")

# Other constants
ASSEMBLY_PREFIX = "assembly:/"
VERSION = "0.2.0 - Second Flight"