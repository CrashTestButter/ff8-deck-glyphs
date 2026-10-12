/* deckglyphs.dll - FF8 Steam Deck Button Glyphs, runtime part.
 *
 * The Timber train mission explains its keypad with a dialogue "diamond" (tilink1 #10, tilink2 #7,
 * tiagit5 #58):
 *
 *       {Triangle}4
 *   {Square}3 {Circle}1
 *       {Cross}2
 *
 * Each icon stands for a game command; FFNx (ff8_use_gamepad_icons) draws it as the glyph of the
 * button that command is bound to. So with a custom binding the glyphs land in the wrong corners.
 * This DLL rearranges the (icon, number) pairs before the window text is rendered so that every pair
 * sits where its physical button is on the Deck: Y top, X left, B right, A bottom. Pairs bound to a
 * non-face button take the free corners. With the keyboard in use the original layout is restored.
 *
 * Hook: the only call of Text_RenderGlyphs (0x4A1570) at 0x49FD14 in the window draw 0x49FC10;
 * the window's message text is at win+8 and is rewritten in place (same length, idempotent).
 * Addresses: FF8_EN.exe, Steam 2013, 1.2 US English.
 */
#include <stdint.h>

typedef int BOOL;
typedef unsigned long DWORD;
typedef void *HANDLE;
typedef const char *LPCSTR;
#define WINAPI __stdcall
#define DLL_PROCESS_ATTACH 1
#define PAGE_EXECUTE_READWRITE 0x40
#define GENERIC_WRITE 0x40000000
#define FILE_SHARE_READ 1
#define CREATE_ALWAYS 2
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)

__declspec(dllimport) BOOL WINAPI VirtualProtect(void *, uintptr_t, DWORD, DWORD *);
__declspec(dllimport) BOOL WINAPI FlushInstructionCache(HANDLE, const void *, uintptr_t);
__declspec(dllimport) HANDLE WINAPI GetCurrentProcess(void);
__declspec(dllimport) DWORD WINAPI GetModuleFileNameA(HANDLE, char *, DWORD);
__declspec(dllimport) HANDLE WINAPI CreateFileA(LPCSTR, DWORD, DWORD, void *, DWORD, DWORD, HANDLE);
__declspec(dllimport) BOOL WINAPI WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);
__declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);

#define CALL_SITE        0x0049FD14u /* E8 -> Text_RenderGlyphs */
#define TEXT_RENDER      0x004A1570u /* void __cdecl (uint32_t *ot, win_obj *win) */
#ifndef DECKGLYPHS_TEST
#define GET_COMMAND_KEY  0x00468260u /* int __cdecl (int is_gamepad, int psx_bit, int 0): DIK / 224+button */
#define GAMEPAD_IN_USE   ((volatile uint8_t *)0x00B8600Eu)
#endif

typedef void(__cdecl *text_render_t)(uint32_t *, uint8_t *);
typedef int(__cdecl *get_command_key_t)(int, int, int);

static HANDLE g_log = INVALID_HANDLE_VALUE;

static void log_str(const char *s)
{
    DWORD n = 0, w;
    if (g_log == INVALID_HANDLE_VALUE) return;
    while (s[n]) n++;
    WriteFile(g_log, s, n, &w, 0);
}

/* Diamond pairs in the original text order: top, left, right, bottom. FF8 text: 0x05 <0x30+n> is
 * icon 0x80+n, digits '1'..'4' are 0x22..0x25. */
enum { N = 4 };
static const uint8_t SLOT_ICON[N]   = {0x34, 0x37, 0x35, 0x36}; /* Triangle, Square, Circle, Cross */
static const uint8_t SLOT_BUTTON[N] = {3, 2, 1, 0};             /* DirectInput: Y, X, B, A (steam_stock_launcher) */

static uint8_t digit_of(uint8_t icon)
{
    switch (icon) {
    case 0x35: return 0x22; /* Circle   1 */
    case 0x36: return 0x23; /* Cross    2 */
    case 0x37: return 0x24; /* Square   3 */
    case 0x34: return 0x25; /* Triangle 4 */
    }
    return 0;
}

/* Physical button FFNx will show for icon 0x80+n, as in ff8_draw_gamepad_icon_or_keyboard_key. */
static int button_of(uint8_t icon, int gamepad)
{
    get_command_key_t key = (get_command_key_t)GET_COMMAND_KEY;
    int bit = icon - 0x30;
    int v = key(gamepad, bit, 0) & 0xFF;
    if (v == 0) v = key(!gamepad, bit, 0) & 0xFF;
    v -= 224;
    return v >= 0 && v < 10 ? v : -1;
}

static void fix_diamond(uint8_t *t)
{
    uint8_t *pos[N];
    int found = 0, i, s;
    uint8_t seen = 0;
    if (!t) return;
    for (i = 0; t[i] && i < 1024; i++) {
        if (t[i] != 0x05 || t[i + 1] < 0x34 || t[i + 1] > 0x37 || t[i + 2] != digit_of(t[i + 1])) continue;
        if (found == N || (seen & (1 << (t[i + 1] - 0x34)))) return; /* not the diamond */
        seen |= 1 << (t[i + 1] - 0x34);
        pos[found++] = t + i;
        i += 2;
    }
    if (found != N) return;

    uint8_t want[N] = {0};
    if (*GAMEPAD_IN_USE) {
        uint8_t used = 0;
        int btn[N];
        for (i = 0; i < N; i++) btn[i] = button_of(SLOT_ICON[i], 1);
        for (s = 0; s < N; s++)          /* face buttons go to their own corner */
            for (i = 0; i < N; i++)
                if (!(used & (1 << i)) && btn[i] == SLOT_BUTTON[s]) { want[s] = SLOT_ICON[i]; used |= 1 << i; break; }
        for (s = 0; s < N; s++)          /* everything else fills the free corners */
            for (i = 0; !want[s] && i < N; i++)
                if (!(used & (1 << i))) { want[s] = SLOT_ICON[i]; used |= 1 << i; }
    } else {
        for (s = 0; s < N; s++) want[s] = SLOT_ICON[s];
    }

    int changed = 0;
    for (s = 0; s < N; s++)
        if (pos[s][1] != want[s]) { pos[s][1] = want[s]; pos[s][2] = digit_of(want[s]); changed = 1; }
    if (changed) {
        static const char *name[] = {"Tri", "Cir", "Crs", "Sqr"};
        static const char head[] = "diamond: top/left/right/bottom =";
        char line[64];
        int n = 0;
        while (head[n]) { line[n] = head[n]; n++; }
        for (s = 0; s < N; s++) {
            const char *p = name[want[s] - 0x34];
            line[n++] = ' ';
            while (*p) line[n++] = *p++;
        }
        line[n++] = '\n';
        line[n] = 0;
        log_str(line);
    }
}

static void __cdecl text_render_hook(uint32_t *ot, uint8_t *win)
{
    fix_diamond(*(uint8_t **)(win + 8));
    ((text_render_t)TEXT_RENDER)(ot, win);
}

static int bytes_equal(uintptr_t a, const uint8_t *b, int n)
{
    for (int i = 0; i < n; i++)
        if (((const uint8_t *)a)[i] != b[i]) return 0;
    return 1;
}

static int is_game_process(void)
{
    char path[520];
    DWORD n = GetModuleFileNameA(0, path, sizeof(path)), i = n;
    while (i && path[i - 1] != '\\' && path[i - 1] != '/') i--;
    const char *b = path + i, *want = "ff8_en.exe";
    for (i = 0; want[i]; i++) {
        char c = b[i];
        if (c >= 'A' && c <= 'Z') c += 32;
        if (c != want[i]) return 0;
    }
    return b[i] == 0;
}

static void install(void)
{
    static const uint8_t site[5]   = {0xE8, 0x57, 0x18, 0x00, 0x00};
    static const uint8_t render[4] = {0x83, 0xEC, 0x28, 0x53};
    static const uint8_t key[4]    = {0x8B, 0x44, 0x24, 0x04};
    DWORD old;
    g_log = CreateFileA("deckglyphs.log", GENERIC_WRITE, FILE_SHARE_READ, 0, CREATE_ALWAYS, 0x80, 0);
    log_str("deckglyphs 0.6\n");
    if (!bytes_equal(CALL_SITE, site, 5) || !bytes_equal(TEXT_RENDER, render, 4) || !bytes_equal(GET_COMMAND_KEY, key, 4)) {
        log_str("unknown FF8_EN.exe (bytes differ), train diamond fix disabled\n");
        return;
    }
    if (!VirtualProtect((void *)CALL_SITE, 5, PAGE_EXECUTE_READWRITE, &old)) {
        log_str("VirtualProtect failed\n");
        return;
    }
    *(int32_t *)(CALL_SITE + 1) = (int32_t)((uintptr_t)text_render_hook - (CALL_SITE + 5));
    VirtualProtect((void *)CALL_SITE, 5, old, &old);
    FlushInstructionCache(GetCurrentProcess(), (void *)CALL_SITE, 5);
    log_str("hooked Text_RenderGlyphs call at 0x49FD14\n");
}

BOOL WINAPI DllMain(HANDLE inst, DWORD reason, void *reserved)
{
    (void)inst; (void)reserved;
    if (reason == DLL_PROCESS_ATTACH && is_game_process()) install();
    return 1;
}
