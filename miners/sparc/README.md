# RustChain SPARC miner (vintage hardware port)

Plain C89 miner for **real SPARC hardware** running SunOS 4.x, Solaris 2.x-10
or NetBSD/sparc. No floating point, no TLS, no dependency beyond libc and BSD
sockets — the toolchains on these machines cannot build the Python miner.

## Architecture coverage

`miner.c` reports one of the node's existing SPARC multiplier buckets:

- `sparc_v7`   — sun4c / sun4m, 32-bit SPARC V7
- `sparc_v8`   — 32-bit SPARC V8 (`__sparc__`)
- `ultrasparc` — 64-bit SPARC V9 / UltraSPARC (`__sparcv9`, `sun4u`, `sun4v`)

`device_model` is taken straight from `uname().machine`, so `sun4c`, `sun4m`,
`sun4u` and `sun4v` show up verbatim in the attestation payload.

## Pinned toolchains

| Target OS        | Toolchain (pinned)              | Flags             |
|------------------|---------------------------------|-------------------|
| SunOS 4.1.4      | gcc 2.7.2.3                     | `-ansi`           |
| Solaris 8/9/10   | gcc 3.4.6                       | `-ansi -pedantic` |
| NetBSD/sparc 9.x | gcc 10.5.0 (pkgsrc/lang/gcc10)  | `-ansi -pedantic` |

## Build

    make CC=gcc

or directly:

    cc -ansi -pedantic -O2 -o rustchain_sparc miner.c

## Run

    RUSTCHAIN_NODE_HOST=50.28.86.131 \
    RUSTCHAIN_NODE_PORT=8080 \
    RUSTCHAIN_MINER_ID=my-sparcstation \
    ./rustchain_sparc

Environment:

- `RUSTCHAIN_NODE_HOST` — node hostname or IP (default `localhost`)
- `RUSTCHAIN_NODE_PORT` — node HTTP port (default `8080`)
- `RUSTCHAIN_MINER_ID`  — miner id, sanitised to `[A-Za-z0-9._-]`

## Hardware proof required for the bounty

1. `uname -a` from the machine (`SunOS ... sun4m` or `NetBSD ... sparc`).
2. `dmesg` / `prtconf` output showing the CPU model.
3. The `payload:` and `response:` lines printed by `rustchain_sparc`.
4. A photo of the running machine with the terminal visible.
