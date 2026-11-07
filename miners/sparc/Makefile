# RustChain SPARC miner build.
#
# Pinned toolchains:
#   SunOS 4.1.4      : gcc 2.7.2.3          (-ansi)
#   Solaris 8/9/10   : gcc 3.4.6            (-ansi -pedantic)
#   NetBSD/sparc 9.x : gcc 10.5.0 (pkgsrc)  (-ansi -pedantic)

CC      ?= cc
CFLAGS  ?= -ansi -pedantic -O2
LDFLAGS ?=
TARGET   = rustchain_sparc

all: $(TARGET)

$(TARGET): miner.c http_client.h
	$(CC) $(CFLAGS) -o $(TARGET) miner.c $(LDFLAGS)

clean:
	rm -f $(TARGET)

.PHONY: all clean
