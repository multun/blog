all: style.css

SCSS_FILES = _default.scss _404.scss _mixins.scss

pygments.css:
	pygmentize -S default -f html -a .highlight -O nobackground=True -o $@

style.css: main.scss $(SCSS_FILES) pygments.css
	sassc $< $@
