// Copyright (c) Meta Platforms, Inc. and affiliates.
//
// Juno - black duck, suit and sunglasses - as a 64x64 pixel avatar.
// Sibling renderer to avatar/muse_pixel.c (Jollybot): same grid, same
// pose, same scale/alpha contract. The character itself is a set of
// palette sprite maps (juno_sprites.h) designed with
// tools/make_juno.py; this file is the life around them - blink and
// breath timing, talk/happy selection, the aura and floor shadow,
// and the strip scalers the LVGL decoder serves.

#include "juno_pixel.h"

#include <math.h>
#include <string.h>

#include "juno_sprites.h"

#define W MUSE_PX_W
#define H MUSE_PX_H

/* ------------------------------------------------------------------ */
/* Palette (indices into s_pal; letters match juno_sprites.h)          */
/* ------------------------------------------------------------------ */

enum {
    P_BG = 0,
    P_OUT, P_FUR, P_FURSH, P_FURHI, P_LENS, P_FRAME, P_WHITE,
    P_BILL, P_BILLSH, P_BILLLN, P_SUIT, P_SUITS, P_LAPEL, P_TIE,
    P_MOUTH, P_SHADOW, P_AURA, P_HEART, P_COUNT,
};

static uint16_t s_pal[P_COUNT];
static bool s_pal_init;

static uint16_t to565(uint32_t c)
{
    uint32_t r = (c >> 16) & 0xff, g = (c >> 8) & 0xff, b = c & 0xff;
    return (uint16_t)(((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3));
}

static void pal_init(void)
{
    if (s_pal_init) return;
    s_pal[P_OUT]    = to565(0x14100e);
    s_pal[P_FUR]    = to565(0x17181c);
    s_pal[P_FURSH]  = to565(0x23242a);
    s_pal[P_FURHI]  = to565(0x3a3c48);
    s_pal[P_LENS]   = to565(0x1a2436);
    s_pal[P_FRAME]  = to565(0x586272);
    s_pal[P_WHITE]  = to565(0xf5f2ea);
    s_pal[P_BILL]   = to565(0xf7b731);
    s_pal[P_BILLSH] = to565(0xe8890c);
    s_pal[P_BILLLN] = to565(0xb85f00);
    s_pal[P_SUIT]   = to565(0x252a36);
    s_pal[P_SUITS]  = to565(0x282931);
    s_pal[P_LAPEL]  = to565(0x565d6e);
    s_pal[P_TIE]    = to565(0x0c0c10);
    s_pal[P_MOUTH]  = to565(0x5b2c14);
    s_pal[P_SHADOW] = to565(0x16101f);
    s_pal[P_HEART]  = to565(0xff4f8b);
    s_pal_init = true;
}

static int pal_of(char c)
{
    switch (c) {
    case 'K': return P_OUT;
    case 'B': return P_FUR;
    case 'b': return P_FURSH;
    case 'H': return P_FURHI;
    case 'G': return P_LENS;
    case 'g': return P_FRAME;
    case 'W': return P_WHITE;
    case 'Y': return P_BILL;
    case 'O': return P_BILLSH;
    case 'o': return P_BILLLN;
    case 'S': return P_SUIT;
    case 's': return P_SUITS;
    case 'L': return P_LAPEL;
    case 'T': return P_TIE;
    case 'M': return P_MOUTH;
    case 'A': return P_AURA;
    case 'R': return P_HEART;
    default:  return P_BG;
    }
}

/* Per-mode accent, same table as Jollybot's schemes. */
static const uint32_t ACCENTS[MUSE_MODE_COUNT] = {
    [MUSE_MODE_BOOT]      = 0xa9c0ff,
    [MUSE_MODE_IDLE]      = 0xa77dff,
    [MUSE_MODE_LISTENING] = 0x5cb8ff,
    [MUSE_MODE_THINKING]  = 0xe07bff,
    [MUSE_MODE_SPEAKING]  = 0x6ff0bf,
    [MUSE_MODE_ERROR]     = 0xff5c5c,
    [MUSE_MODE_OFF]       = 0x7c72d0,
};

uint32_t juno_pixel_accent(muse_mode_t mode)
{
    if (mode < 0 || mode >= MUSE_MODE_COUNT) mode = MUSE_MODE_IDLE;
    return ACCENTS[mode];
}

/* ------------------------------------------------------------------ */
/* Framebuffer                                                         */
/* ------------------------------------------------------------------ */

static uint8_t s_fb[W * H];
static uint8_t s_mask[W * H];
static uint16_t (*s_bg_hook)(int grid_row);

void juno_pixel_set_bg_hook(uint16_t (*fn)(int grid_row))
{
    s_bg_hook = fn;
}

static uint32_t s_rng = 0x2545f491u;
static float frand(void)
{
    s_rng = s_rng * 1664525u + 1013904223u;
    return ((s_rng >> 9) & 0x7fffff) / 8388608.0f;
}

static void draw_shadow(void)
{
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            float d = ((x - 32.0f) / 17.0f) * ((x - 32.0f) / 17.0f)
                    + ((y - 60.0f) / 3.0f) * ((y - 60.0f) / 3.0f);
            if (d <= 1.0f) {
                s_fb[y * W + x] = P_SHADOW;
                s_mask[y * W + x] = 110;
            }
        }
    }
}

static float clampf01(float v)
{
    return v < 0.0f ? 0.0f : v > 1.0f ? 1.0f : v;
}

static void draw_aura(const muse_pose_t *p)
{
    uint32_t acc = juno_pixel_accent(p->mode);
    s_pal[P_AURA] = to565(acc);
    float pulse = 0.85f + 0.15f * sinf(p->t * 1.7f);
    /* Boot: the aura fades in over 1.4 s, like Jollybot's. */
    float bootf = p->mode == MUSE_MODE_BOOT ? clampf01(p->mode_t / 1.4f) : 1.0f;
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            float d = ((x - 32.0f) / 25.0f) * ((x - 32.0f) / 25.0f)
                    + ((y - 30.0f) / 27.0f) * ((y - 30.0f) / 27.0f);
            if (d < 1.0f && s_mask[y * W + x] == 0) {
                float a = (1.0f - d) * 90.0f * pulse * bootf;
                s_fb[y * W + x] = P_AURA;
                s_mask[y * W + x] = (uint8_t)a;
            }
        }
    }
}

static void stamp(const char *const *rows, int yoff)
{
    for (int y = 0; y < H; y++) {
        int sy = y - yoff;
        if (sy < 0 || sy >= H) continue;
        const char *row = rows[sy];
        for (int x = 0; x < W; x++) {
            int idx = pal_of(row[x]);
            if (idx != P_BG) {
                s_fb[y * W + x] = (uint8_t)idx;
                s_mask[y * W + x] = 255;
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/* Render                                                              */
/* ------------------------------------------------------------------ */

static float s_next_blink = 2.2f;
static float s_blink_start = -10.0f;

void juno_pixel_render(const muse_pose_t *pose)
{
    pal_init();
    memset(s_fb, 0, sizeof(s_fb));
    memset(s_mask, 0, sizeof(s_mask));

    if (pose->t >= s_next_blink) {
        s_blink_start = pose->t;
        s_next_blink = pose->t + 2.4f + frand() * 2.6f;
    }
    bool blink = (pose->t - s_blink_start) < 0.13f;

    draw_aura(pose);
    draw_shadow();

    const char *const *map = JUNO_IDLE;
    bool boot = pose->mode == MUSE_MODE_BOOT;
    if (pose->mode == MUSE_MODE_OFF) {
        map = JUNO_SLEEP;
    } else if (boot) {
        /* Waking: lids stay shut until 0.9 s, then open (Jollybot's
         * boot beats) - boot overrides blink/happy while it lasts. */
        map = pose->mode_t < 0.9f ? JUNO_BOOT : JUNO_IDLE;
    } else if (blink) {
        map = JUNO_BLINK;
    } else if (pose->mode == MUSE_MODE_ERROR) {
        map = JUNO_ERROR;
    } else if (pose->mode == MUSE_MODE_LISTENING) {
        map = JUNO_LISTEN;
    } else if (pose->mode == MUSE_MODE_THINKING) {
        map = JUNO_THINK;
    } else if (pose->mode == MUSE_MODE_SPEAKING && pose->level > 0.05f) {
        map = JUNO_TALK;
    } else if (pose->happy > 0.4f) {
        map = JUNO_WAVE;
    } else if (pose->happy > 0.15f) {
        map = JUNO_HAPPY;
    } else if (pose->mode == MUSE_MODE_IDLE) {
        /* Look-around: the gaze wanders on a slow cycle. */
        int phase = ((int)(pose->t / 2.6f)) % 4;
        if (phase == 1) map = JUNO_LOOKL;
        else if (phase == 3) map = JUNO_LOOKR;
    }
    /* Breath: a slow 1 px bob, down on the exhale. */
    int bob = (sinf(pose->t * 1.8f) > 0.55f) ? 1 : 0;
    if (boot) {
        /* Pop-in: start sunk 5 px and rise to rest over 0.6 s (the
         * sprite-space analog of Jollybot's boot squash), then the
         * normal breath bob takes over. */
        float pop = clampf01(pose->mode_t / 0.6f);
        bob = pop < 1.0f ? (int)((1.0f - pop) * 5.0f + 0.5f) : bob;
    }
    stamp(map, bob);
}

/* ------------------------------------------------------------------ */
/* Scalers (same contract as Jollybot's)                               */
/* ------------------------------------------------------------------ */

static int s_size = W;

void juno_pixel_set_size(int px)
{
    s_size = px > 0 ? px : W;
}

void juno_pixel_scale(uint16_t *dst, int stride_px, int x0, int x1, int y0, int y1)
{
    pal_init();
    for (int y = y0; y <= y1; y++) {
        int gy = y * H / s_size;
        if (gy < 0) gy = 0;
        if (gy >= H) gy = H - 1;
        for (int x = x0; x <= x1; x++) {
            int gx = x * W / s_size;
            if (gx < 0) gx = 0;
            if (gx >= W) gx = W - 1;
            uint8_t idx = s_fb[gy * W + gx];
            uint16_t c;
            if (idx == P_BG && s_bg_hook) {
                c = s_bg_hook(gy);
            } else {
                c = s_pal[idx];
            }
            dst[(y - y0) * stride_px + (x - x0)] = c;
        }
    }
}

void juno_pixel_scale_alpha(uint8_t *dst, int stride_px, int x0, int x1, int y0, int y1)
{
    for (int y = y0; y <= y1; y++) {
        int gy = y * H / s_size;
        if (gy < 0) gy = 0;
        if (gy >= H) gy = H - 1;
        for (int x = x0; x <= x1; x++) {
            int gx = x * W / s_size;
            if (gx < 0) gx = 0;
            if (gx >= W) gx = W - 1;
            dst[(y - y0) * stride_px + (x - x0)] = s_mask[gy * W + gx];
        }
    }
}
