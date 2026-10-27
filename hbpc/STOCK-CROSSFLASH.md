# Cross-line stock firmware: CN 3.4.6 on a `B651 NO_EEA_M2` phone

This is a pointer. The subject splits in two, and each half has its own page:

| Page | What is on it |
| --- | --- |
| **[STOCK-CROSSFLASH-INSTALL.md](STOCK-CROSSFLASH-INSTALL.md)** | the commands, in order: what to back up first, the download and the extraction, the unlock, the flash in its two fastboot modes, the checks afterwards, and the rollback to 3.1.6 |
| **[STOCK-CROSSFLASH-INFO.md](STOCK-CROSSFLASH-INFO.md)** | the evidence behind them: what the payload writes and what it leaves alone, `B651 CN` 3.4.6 against `B651 NO_EEA_M2` 3.1.6 partition by partition, what changes on the phone, the `super` arithmetic, the two fastboot modes with their partition lists, the factory image's download list, how to reproduce the analysis, and what is not covered |

**Verdict, in short.** The CN package is the same firmware for the same board: same board
configuration in `lk`, same AVB key, same modem build and band database, same APN database,
same panel overlays, same locale defaults. It writes none of `nvram`, `nvdata`, `proinfo`,
`sec1` or `seccfg`, so the IMEI, the MAC addresses and the RF calibration survive it, and it
moves no anti-rollback index, so the factory 3.1.6 image stays a working way back. What it
costs: `ro.build.versionCode` reads `B651 CN` for good, the CN `product` image carries a much
smaller Google app set, and the bootloader has to be unlocked — which wipes `/data` and turns
verified boot orange.

One phone has been through it end to end, a `B651 NO_EEA_M2` HiBreak Pro Color going
3.1.6 → 3.4.6, and it boots 3.4.6 with its baseband string and Bluetooth address unchanged.
The thing that stops most first attempts is that this device answers `fastboot` in two modes,
each told about a different half of the partition table; both pages say so, and
[STOCK-CROSSFLASH-INFO.md](STOCK-CROSSFLASH-INFO.md#two-fastboot-modes-and-what-each-can-write)
has the two lists and the failure text verbatim.

There is no sideload path — the GPT has no `recovery` partition — the stock updater will never
offer CN firmware to a NO_EEA phone, and the Download-Agent route is deliberately not
documented: the GSI of [README.md](README.md) needs the bootloader unlocked anyway, so the
unlock it would save is one the phone needs regardless.
