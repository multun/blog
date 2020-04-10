# Installation

```sh
python3 -m venv venv
source venv/bin/activate
pip3 install git+https://github.com/getpelican/pelican
pip3 install Markdown # for rendering markdown content
pip3 install html5lib # for simple_footnotes
pip3 install pyscss # for scss preprocessing
pip3 install git+https://github.com/eli-collins/jinja2-htmlcompress
git clone --recursive https://github.com/getpelican/pelican-plugins plugins
pelican content -s pelicanconf.py -t my-theme
```

# TODO

Use https://github.com/getpelican/pelican-plugins/tree/master/assets
