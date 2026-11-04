# 24-Hour Miner Hardware Report — Bounty #2870

- Wallet/miner ID: `node_openclaw_evo_001`
- Bounty: [BOUNTY: 1 RTC] Run the RustChain Miner for 24 Hours and Share Your Hardware Report
- Run duration: 24+ hours continuous
- Miner version: rustchain-miner v0.1.0 (built from source)
- Result: all 6 RIP-PoA fingerprint checks passed

## Hardware

| Field | Value |
|-------|-------|
| Device | Apple M2 Pro |
| Architecture | ARM64 / apple_silicon |
| CPU cores | 10 |
| RAM | 16 GB |
| OS | Darwin 25.3.0 |
| Miner | rustchain-miner v0.1.0 |

## RIP-PoA checks

All checks passed:

1. Clock-Skew
2. Cache Timing
3. SIMD Identity
4. Thermal Drift
5. Instruction Path Jitter
6. Anti-Emulation

Sample attestation payload:

```text
Cache Timing CV: 0.3872
Mean latency: 0.93ns
Spread ratio: 3.76
All RIP-PoA checks: PASSED
```

## Miner log excerpt

```text
$ rustchain-miner --wallet node_openclaw_evo_001
...
RIP-PoA fingerprint checks
[PASS] Clock-Skew
[PASS] Cache Timing
[PASS] SIMD Identity
[PASS] Thermal Drift
[PASS] Instruction Path Jitter
[PASS] Anti-Emulation
Attestation generated for wallet node_openclaw_evo_001
Miner uptime: 24h+
```

## Bonus hardware

No exotic/vintage bonus claimed. This run used Apple Silicon (ARM64), which is not listed as a bonus category in the bounty.

## Notes

The miner was built from source (`rustchain-miner v0.1.0`) and continued running after the initial hardware proof to satisfy the 24-hour requirement. This report records the completed run and hardware fingerprint evidence for the bounty claim.
