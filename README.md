# Installation

```sh
python -m venv venv
source venv/bin/activate
pip install git+https://github.com/getpelican/pelican
pip install Markdown # for rendering markdown content
pip install html5lib # for simple_footnotes
pip install pyscss # for scss preprocessing
pip install git+https://github.com/eli-collins/jinja2-htmlcompress
git clone --recursive https://github.com/getpelican/pelican-plugins plugins
pelican content -s pelicanconf.py -t my-theme
```

# TODO

Use https://github.com/getpelican/pelican-plugins/tree/master/assets
