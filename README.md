# LineageOS 23.2 GSI for the Bigme HiBreak Pro Color

This repository holds patches and a build driver that make LineageOS 23.2
(Android 16) into a system image for the **Bigme HiBreak Pro Color** E-Ink phone.
No other device is supported.

- **Read first:** [hbpc/README.md](hbpc/README.md) covers the features,
  installation, updates, rollback, building from source, known limits, credits and
  license.
- **Download:** <https://sourceforge.net/projects/lineageos-hibreakpro-color/>
  (GApps and Vanilla EXT4 images).
- **Source:** <https://github.com/dianqk/LineageOS_gsi_HBPC>
- **Community guides** for the related HiBreak Pro (bootloader unlock, backup, GSI
  flashing): <https://vbh.ai/blog/>. They are not written for the Pro Color;
  [hbpc/README.md](hbpc/README.md#community-guides-written-for-the-hibreak-pro)
  explains where its steps differ.

This repository forks [MisterZtr/LineageOS_gsi](https://github.com/MisterZtr/LineageOS_gsi)
(`lineage-23.2`). The upstream patch series outside `hbpc/` is unchanged, except for
the deviations in [hbpc/UPSTREAM-DELTA.md](hbpc/UPSTREAM-DELTA.md). This README
replaces upstream's generic build instructions. Build this device's image with
`hbpc/build-hibreak.py`, as described in [hbpc/README.md](hbpc/README.md#building-from-source).

The project was written almost entirely with LLM assistance and is not independently
reviewed. **Use it at your own risk.**

## Credits

LineageOS, TrebleDroid and phh, MisterZtr and the contributors listed in the
[upstream README](https://github.com/MisterZtr/LineageOS_gsi/blob/lineage-23.2/README.md),
damianmqr and vbbot for the E-Ink service. See [hbpc/README.md](hbpc/README.md#credits)
and [hbpc/NOTICE](hbpc/NOTICE).
