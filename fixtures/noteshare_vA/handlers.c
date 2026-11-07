/* Native request helpers (synthetic, decompiled-style). */
#include <stdio.h>
#include <string.h>

#define NAME_MAX 64

/* Copy the request-supplied note name into a fixed buffer, bounded. */
int load_name(char *dst, size_t dst_len, const char *src) {
    if (src == NULL) return -1;
    size_t n = strlen(src);
    if (n >= dst_len) n = dst_len - 1;   /* clamp to buffer size */
    memcpy(dst, src, n);
    dst[n] = '\0';
    return 0;
}

void handle_request(const char *src) {
    char name[NAME_MAX];
    load_name(name, sizeof(name), src);
    printf("loading %s\n", name);
}
