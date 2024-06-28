all: style.css

SASS ?= sass

SCSS_FILES = _default.scss _404.scss _mixins.scss pygments.scss _fonts.scss

pygments.scss:
	which pygmentize && pygmentize -S default -f html -a .highlight -O nobackground=True > $@

style.css: main.scss $(SCSS_FILES) pygments.scss
	$(SASS) $< $@
