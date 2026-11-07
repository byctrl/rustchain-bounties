"""Structural checks for the SPARC vintage miner port.

Runs standalone without pytest (no C compiler or toolchain needed):

    python tests/test_sparc_miner.py

Under pytest the test_* functions are collected as usual.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPARC_DIR = ROOT / "miners" / "sparc"


def _read(name):
    return (SPARC_DIR / name).read_text(encoding="utf-8", errors="replace")


def test_required_files_exist():
    for name in ("miner.c", "http_client.h", "Makefile", "README.md"):
        assert (SPARC_DIR / name).is_file(), "missing miners/sparc/" + name


def test_no_fpu_math():
    src = _read("miner.c")
    for token in ("<math.h>", "float ", "double "):
        assert token not in src, "unexpected FPU token: " + token


def test_sparc_arch_tokens_present():
    src = _read("miner.c")
    for token in ("sparc_v7", "sparc_v8", "ultrasparc", "sun4u", "sun4v"):
        assert token in src, "missing arch token: " + token


def test_plain_http_only():
    src = _read("http_client.h")
    for token in ("openssl", "SSL_", "TLS_"):
        assert token not in src, "TLS dependency found: " + token
    assert "gethostbyname" in src


def test_c89_no_line_comments_in_c_sources():
    for name in ("miner.c", "http_client.h"):
        src = _read(name)
        for line in src.splitlines():
            assert not line.lstrip().startswith("//"), name + ": " + line


def test_toolchain_is_pinned():
    src = _read("README.md")
    assert "gcc 2.7.2.3" in src
    assert "10.5.0" in src


def main():
    test_required_files_exist()
    test_no_fpu_math()
    test_sparc_arch_tokens_present()
    test_plain_http_only()
    test_c89_no_line_comments_in_c_sources()
    test_toolchain_is_pinned()
    print("sparc miner structure: OK")


if __name__ == "__main__":
    main()
