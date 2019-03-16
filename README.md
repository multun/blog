# Installation

```sh
python -m venv venv
source venv/bin/activate
pip install pelican
git clone --recursive https://github.com/getpelican/pelican-plugins plugins
pelican content -s pelicanconf.py -t my-theme
```
