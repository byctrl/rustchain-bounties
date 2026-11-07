/*
 * Minimal plain-HTTP POST client for the RustChain SPARC miner.
 *
 * BSD sockets + gethostbyname only. No TLS, no OpenSSL, no getaddrinfo,
 * so it links on SunOS 4.1.x, Solaris 2.5-10 and NetBSD/sparc.
 */

#ifndef RUSTCHAIN_HTTP_CLIENT_H
#define RUSTCHAIN_HTTP_CLIENT_H

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <arpa/inet.h>

#ifdef __sun
#include <sys/filio.h>
#endif

static int http_post(const char *host, int port, const char *path,
                     const char *body, char *resp, int resp_len)
{
    struct hostent *he;
    struct sockaddr_in addr;
    int sock;
    int sent;
    int n;
    int total;
    int body_len;
    char req[2048];
    char header[512];

    if (resp != NULL && resp_len > 0) {
        resp[0] = '\0';
    }

    he = gethostbyname(host);
    if (he == NULL) {
        fprintf(stderr, "resolve failed for %s\n", host);
        return -1;
    }

    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)port);
    memcpy(&addr.sin_addr, he->h_addr, he->h_length);

    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("socket");
        return -1;
    }

    if (connect(sock, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("connect");
        close(sock);
        return -1;
    }

    body_len = (int)strlen(body);
    sprintf(header,
            "POST %s HTTP/1.0\r\n"
            "Host: %s\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n",
            path, host, body_len);

    if ((int)(strlen(header) + (size_t)body_len) >= (int)sizeof req) {
        fprintf(stderr, "request too large\n");
        close(sock);
        return -1;
    }
    strcpy(req, header);
    strcat(req, body);

    total = (int)strlen(req);
    sent = 0;
    while (sent < total) {
        n = (int)send(sock, req + sent, total - sent, 0);
        if (n <= 0) {
            perror("send");
            close(sock);
            return -1;
        }
        sent += n;
    }

    total = 0;
    if (resp != NULL && resp_len > 1) {
        while (total < resp_len - 1) {
            n = (int)recv(sock, resp + total, resp_len - 1 - total, 0);
            if (n <= 0) {
                break;
            }
            total += n;
        }
        resp[total] = '\0';
    }

    close(sock);
    return 0;
}

#endif
