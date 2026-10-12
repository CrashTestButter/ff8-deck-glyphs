/* Host test of fix_diamond: cc -m32 not needed, the logic is plain C.  Run: tools/test.sh */
#include <stdio.h>
#include <string.h>
#define DECKGLYPHS_TEST
static unsigned char g_gamepad = 1;
static int g_bind[8]; /* psx bit -> 224 + button */
static int __attribute__((unused)) fake_key(int pad, int bit, int z) { (void)pad; (void)z; return g_bind[bit]; }
#define GET_COMMAND_KEY ((uintptr_t)fake_key)
#define GAMEPAD_IN_USE (&g_gamepad)
#define __stdcall
#define __declspec(x)
#define __cdecl
#include "../src/deckglyphs.c"

BOOL VirtualProtect(void *a, uintptr_t b, DWORD c, DWORD *d) { (void)a; (void)b; (void)c; (void)d; return 0; }
BOOL FlushInstructionCache(HANDLE a, const void *b, uintptr_t c) { (void)a; (void)b; (void)c; return 0; }
HANDLE GetCurrentProcess(void) { return 0; }
DWORD GetModuleFileNameA(HANDLE a, char *b, DWORD c) { (void)a; (void)c; b[0] = 0; return 0; }
HANDLE CreateFileA(LPCSTR a, DWORD b, DWORD c, void *d, DWORD e, DWORD f, HANDLE g) { (void)a; (void)b; (void)c; (void)d; (void)e; (void)f; (void)g; return INVALID_HANDLE_VALUE; }
BOOL WriteFile(HANDLE a, const void *b, DWORD c, DWORD *d, void *e) { (void)a; (void)b; (void)c; (void)d; (void)e; return 1; }

static const unsigned char DIAMOND[] = {0x20,0x20,5,0x34,0x25,2,5,0x37,0x24,0x20,5,0x35,0x22,2,0x20,0x20,5,0x36,0x23,0};
static void show(const unsigned char *t) {
    const char *nm[] = {"Tri","Cir","Crs","Sqr"};
    for (int i = 0; t[i]; i++) if (t[i] == 5) { printf("%s%c ", nm[t[i+1]-0x34], '0' + t[i+2] - 0x21); i += 2; }
    printf("\n");
}
static void run(const char *what, int tri, int cir, int crs, int sqr, int pad) {
    unsigned char t[sizeof DIAMOND]; memcpy(t, DIAMOND, sizeof t);
    g_bind[4] = 224 + tri; g_bind[5] = 224 + cir; g_bind[6] = 224 + crs; g_bind[7] = 224 + sqr; g_gamepad = pad;
    fix_diamond(t);
    printf("%-34s top/left/right/bottom: ", what); show(t);
    unsigned char u[sizeof t]; memcpy(u, t, sizeof u); fix_diamond(u);
    if (memcmp(t, u, sizeof t)) printf("  NOT IDEMPOTENT\n");
}
int main(void) {
    /* buttons: 0 A, 1 B, 2 X, 3 Y, 4 L1 */
    run("default (Tri=Y Cir=B Crs=A Sqr=X)", 3, 1, 0, 2, 1);
    run("A confirm (Cir=A Crs=B)", 3, 0, 1, 2, 1);
    run("user (Cir=Y Crs=A Sqr=X Tri=B)", 1, 3, 0, 2, 1);
    run("Tri on L1 (Y free)", 4, 1, 0, 2, 1);
    run("keyboard restores original", 4, 0, 1, 2, 0);
    return 0;
}
