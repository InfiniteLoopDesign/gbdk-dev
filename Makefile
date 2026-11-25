ROM := build/blank.gbc
LCC ?= lcc

.PHONY: all clean
all: $(ROM)

$(ROM): src/main.c Makefile
	mkdir -p $(@D)
	$(LCC) -Wm-yC -Wm-ynGBDKBLANK -o $(@D)/blank.tmp.gbc $<
	mv $(@D)/blank.tmp.gbc $@

clean:
	rm -rf build
