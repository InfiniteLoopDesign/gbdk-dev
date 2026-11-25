#include <gb/cgb.h>
#include <gb/gb.h>

#define SCREEN_COLOR RGB_WHITE

static const uint8_t blank_tile[16] = {0};

void main(void) {
    DISPLAY_OFF;
    set_bkg_data(0, 1, blank_tile);
    fill_bkg_rect(0, 0, 20, 18, 0);
    fill_bkg_rect_attributes(0, 0, 20, 18, 0);
    set_bkg_palette_entry(0, 0, SCREEN_COLOR);
    SHOW_BKG;
    DISPLAY_ON;

    // Add your game loop here.
    while (1) {
        vsync();
    }
}
