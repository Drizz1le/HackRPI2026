/* Native request helpers (synthetic, decompiled-style). */
#include <stdio.h>
#include <string.h>

#define NAME_MAX 64

/* planted: attacker-controlled name copied into a fixed stack buffer with
   no bounds check -> stack buffer overflow (dst_len ignored). */
int load_name(char *dst, size_t dst_len, const char *src) {
    if (src == NULL) return -1;
    strcpy(dst, src);
    return 0;
}

void handle_request(const char *src) {
    char name[NAME_MAX];
    load_name(name, sizeof(name), src);
    printf("loading %s\n", name);
}
