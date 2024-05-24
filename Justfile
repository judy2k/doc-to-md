clean:
    rm -rf dist src/doctomd/__pycache__

test:
    pytest

icons:
    python scripts/make_icon.py assets/mac_icon.png assets/app_icon.icns 1024,512,256,64,32
    cp assets/app_icon.icns src/doctomd/resources/