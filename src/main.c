#include <gb/cgb.h>
#include <gb/gb.h>
#include <gbdk/console.h>
#include <stdbool.h>
#include <stdio.h>

#define LIGHT_COUNT 5u
#define LIGHT_Y 48u
#define LIT_PALETTE 1u
#define FACE_COLOR 2u
#define DARK_RED RGB(9, 2, 4)
#define BRIGHT_RED RGB(31, 4, 5)
#define TIMEOUT_TICKS (3u * 4096u)

static const palette_color_t background[] = {
    RGB(4, 5, 8), RGB(8, 10, 14), RGB(17, 19, 22), RGB(28, 29, 31)
};

static const palette_color_t dim_light[] = {
    0, RGB(18, 18, 20), DARK_RED, 0
};

// Mirror this 8x8 tile in both directions to make a 16x16 light.
static const uint8_t light_corner[] = {
    0x07, 0x00,
    0x18, 0x07,
    0x20, 0x1f,
    0x40, 0x3f,
    0x40, 0x3f,
    0x80, 0x7f,
    0x80, 0x7f,
    0x80, 0x7f
};

static const uint8_t corner_flips[] = {
    0, S_FLIPX, S_FLIPY, S_FLIPX | S_FLIPY
};

static void set_light(uint8_t light, uint8_t palette) {
    for (uint8_t corner = 0; corner < 4u; ++corner) {
        set_sprite_prop(light * 4u + corner, S_BANK | corner_flips[corner] | S_PAL(palette));
    }
}

static void init_lights(void) {
    // Use VRAM bank 1 so the sprites never overwrite the console font.
    VBK_REG = 1;
    set_sprite_data(0, 1, light_corner);
    VBK_REG = 0;

    SPRITES_8x8;
    set_sprite_palette(0, 1, dim_light);
    set_sprite_palette(LIT_PALETTE, 1, dim_light);

    for (uint8_t light = 0; light < LIGHT_COUNT; ++light) {
        set_light(light, 0);
        for (uint8_t corner = 0; corner < 4u; ++corner) {
            uint8_t sprite = light * 4u + corner;
            set_sprite_tile(sprite, 0);
            move_sprite(sprite, 24u + light * 28u + (corner & 1u) * 8u,
                        LIGHT_Y + 16u + (corner >> 1u) * 8u);
        }
    }
    SHOW_SPRITES;
}

static bool pressed_a(void) {
    static uint8_t previous_a;
    uint8_t current_a = joypad() & J_A;
    bool pressed = current_a && !previous_a;
    previous_a = current_a;
    return pressed;
}

static void show_status(const char *message) {
    gotoxy(2, 10);
    printf("                ");
    gotoxy(2, 10);
    printf("%s", message);
}

static bool wait_frames(uint8_t count) {
    uint8_t start = (uint8_t)sys_time;
    do {
        if (pressed_a()) {
            return false;
        }
    } while ((uint8_t)((uint8_t)sys_time - start) < count);
    return true;
}

static bool countdown(uint8_t hold_frames) {
    for (uint8_t light = 0; light < LIGHT_COUNT; ++light) {
        if (!wait_frames(60u)) {
            return false;
        }
        set_light(light, LIT_PALETTE);
    }
    return wait_frames(hold_frames);
}

static bool wait_for_lights_out(void) {
    // The first colored pixels appear on LIGHT_Y + 1 after VBlank.
    while (LY_REG >= 144u || LY_REG < LIGHT_Y + 1u) {
        if (pressed_a()) {
            return false;
        }
    }
    return true;
}

static uint16_t measure_reaction(void) {
    uint16_t ticks = 0;
    uint8_t previous_tick = TIMA_REG;

    // Poll between frames. The 8-bit delta also works when TIMA wraps.
    while (ticks < TIMEOUT_TICKS) {
        bool pressed = pressed_a();
        uint8_t tick = TIMA_REG;
        ticks += (uint8_t)(tick - previous_tick);
        if (pressed) {
            break;
        }
        previous_tick = tick;
    }
    return ticks;
}

static void play_round(void) {
    // Mix the frame count with a running divider at the player's starting press.
    uint8_t hold_frames = 45u + ((DIV_REG ^ (uint8_t)sys_time) & 127u);
    vsync();
    for (uint8_t light = 0; light < LIGHT_COUNT; ++light) {
        set_light(light, 0);
    }
    // Let OAM copy the dim palette assignments before restoring the red.
    vsync();
    set_sprite_palette_entry(LIT_PALETTE, FACE_COLOR, BRIGHT_RED);
    show_status("Wait...");

    bool start = countdown(hold_frames);
    if (!start) {
        vsync();
    }
    // One palette write turns all five faces dark in the same frame.
    set_sprite_palette_entry(LIT_PALETTE, FACE_COLOR, DARK_RED);
    if (!start || !wait_for_lights_out()) {
        show_status("Jump start!");
        return;
    }

    uint16_t ticks = measure_reaction();
    if (ticks >= TIMEOUT_TICKS) {
        show_status("Too slow!");
        return;
    }

    // Convert the 4096 Hz clock to milliseconds, rounding to the nearest ms.
    unsigned int milliseconds = (ticks * 125UL + 256UL) / 512UL;
    show_status("");
    printf("%u ms", milliseconds);
}

void main(void) {
    gotoxy(4, 2);
    printf("GREEN LIGHT");
    gotoxy(3, 4);
    printf("REACTION TEST");
    gotoxy(2, 13);
    printf("A on lights out");
    gotoxy(2, 15);
    printf("A to start/retry");
    show_status("Ready");

    DISPLAY_OFF;
    set_bkg_palette(0, 1, background);
    init_lights();
    DISPLAY_ON;

    // At normal CPU speed TIMA advances 4096 times per second.
    TMA_REG = 0;
    TAC_REG = TACF_START | TACF_4KHZ;

    while (1) {
        if (pressed_a()) {
            play_round();
        }
    }
}
