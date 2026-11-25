ROM := build/green-light.gbc
LCC ?= lcc

.PHONY: all clean
all: $(ROM)

$(ROM): src/main.c Makefile
	mkdir -p $(@D)
	$(LCC) -Wm-yC -Wm-ynGREENLIGHT -o $(@D)/green-light.tmp.gbc $<
	mv $(@D)/green-light.tmp.gbc $@

clean:
	rm -rf build
