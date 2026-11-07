/*
 * RustChain SPARC miner (vintage hardware port).
 *
 * Targets real SPARC hardware running:
 *   - SunOS 4.1.x
 *   - Solaris 2.5 - 10
 *   - NetBSD/sparc
 *
 * Portable C89/C90. No floating point, no TLS, no external libraries.
 * Architecture families reported: sparc_v7, sparc_v8, ultrasparc.
 * uname() machine strings recognised: sun4c, sun4m, sun4u, sun4v.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/utsname.h>

#include "http_client.h"

#ifndef RUSTCHAIN_DEFAULT_PORT
#define RUSTCHAIN_DEFAULT_PORT 8080
#endif

#ifndef RUSTCHAIN_BODY_MAX
#define RUSTCHAIN_BODY_MAX 1024
#endif

#define RUSTCHAIN_MINER_VERSION "sparc-c89-1.0"

static const char *device_arch(void)
{
#if defined(__sparcv9) || defined(__sparc_v9__) || defined(__arch64__)
    return "ultrasparc";
#elif defined(__sparc__) || defined(__sparc)
    return "sparc_v8";
#else
    return "sparc_v7";
#endif
}

static int env_int(const char *name, int dflt)
{
    const char *value;

    value = getenv(name);
    if (value == NULL || value[0] == '\0') {
        return dflt;
    }
    return atoi(value);
}

static const char *env_str(const char *name, const char *dflt)
{
    const char *value;

    value = getenv(name);
    if (value == NULL || value[0] == '\0') {
        return dflt;
    }
    return value;
}

static void sanitize(char *dst, const char *src, int dst_len)
{
    int i;
    int j;
    char c;

    j = 0;
    for (i = 0; src[i] != '\0' && j < dst_len - 1; i++) {
        c = src[i];
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.') {
            dst[j] = c;
            j++;
        }
    }
    dst[j] = '\0';
    if (j == 0) {
        strcpy(dst, "sparc-anon");
    }
}

static int cpu_count(void)
{
#if defined(_SC_NPROCESSORS_ONLN)
    long n;

    n = sysconf(_SC_NPROCESSORS_ONLN);
    if (n < 1) {
        return 1;
    }
    return (int)n;
#else
    return 1;
#endif
}

static int memory_mb(void)
{
#if defined(_SC_PHYS_PAGES) && defined(_SC_PAGESIZE)
    long pages;
    long page_size;

    pages = sysconf(_SC_PHYS_PAGES);
    page_size = sysconf(_SC_PAGESIZE);
    if (pages < 1 || page_size < 1) {
        return 0;
    }
    return (int)((pages / 1024L) * (page_size / 1024L));
#else
    return 0;
#endif
}

int main(void)
{
    struct utsname uts;
    char miner_id[64];
    char host[128];
    char body[RUSTCHAIN_BODY_MAX];
    char resp[2048];
    const char *raw_id;
    const char *raw_host;
    int port;
    int rc;
    long now;

    raw_id = env_str("RUSTCHAIN_MINER_ID", "sparc-anon");
    sanitize(miner_id, raw_id, (int)sizeof miner_id);

    raw_host = env_str("RUSTCHAIN_NODE_HOST", "localhost");
    strncpy(host, raw_host, sizeof host - 1);
    host[sizeof host - 1] = '\0';

    port = env_int("RUSTCHAIN_NODE_PORT", RUSTCHAIN_DEFAULT_PORT);

    if (uname(&uts) != 0) {
        strcpy(uts.sysname, "unknown");
        strcpy(uts.release, "unknown");
        strcpy(uts.machine, "sparc");
    }

    now = (long)time((time_t *)0);

    sprintf(body,
            "{\"miner\":\"%s\","
            "\"device_family\":\"sparc\","
            "\"device_arch\":\"%s\","
            "\"device_model\":\"%s\","
            "\"os\":\"%s %s\","
            "\"cores\":%d,"
            "\"memory_mb\":%d,"
            "\"timestamp\":%ld,"
            "\"miner_version\":\"%s\"}",
            miner_id,
            device_arch(),
            uts.machine,
            uts.sysname,
            uts.release,
            cpu_count(),
            memory_mb(),
            now,
            RUSTCHAIN_MINER_VERSION);

    printf("RustChain SPARC miner %s\n", RUSTCHAIN_MINER_VERSION);
    printf("node: %s:%d\n", host, port);
    printf("payload: %s\n", body);

    rc = http_post(host, port, "/attest", body, resp, (int)sizeof resp);
    if (rc != 0) {
        fprintf(stderr, "attestation failed\n");
        return 1;
    }

    printf("response: %s\n", resp);
    return 0;
}
