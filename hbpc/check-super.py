#!/usr/bin/env python3
"""Check that every byte of the extracted images is inside a built super image.

    check-super.py super-check.img extracted

`super-check.img` must be linear: run `simg2img super.img super-check.img` first, because
lpdump cannot read a sparse file. Where each partition's bytes live is read back out of the
image with lpdump rather than taken from the lpmake command line, so this catches an image
lpmake skipped or laid out differently, and it checks the map a flasher would honour.

A partition whose data lpmake split across several extents — which it does for a sparse
image with holes in it — is followed extent by extent, each against its own slice of the
source file.
"""
import os
import re
import subprocess
import sys

SECTOR = 512
CHUNK = 8 << 20
SIMDUMP_MAGIC = b"\x3a\xff\x26\xed"

# "super: 2048 .. 2560: system_a (512 sectors)", the lines under lpdump's
# "Super partition layout:". The end sector is exclusive; the sector count gives the
# length directly, so the line is all that is needed apart from the partition offset.
LAYOUT_ROW = re.compile(
    r"^(\S+):\s+(\d+)\s+\.\.\s+(\d+):\s+(\S+)\s+\((\d+)\s+sectors\)$")
# The blocks under "Partition table:" of the same output, used when the layout section is
# missing (older lpdump prints one flat table instead of both). They carry the
# partition-relative target offset, which the layout rows do not.
BLOCK_NAME = re.compile(r"^\s+Name:\s+(\S+)\s*$")
BLOCK_EXTENT = re.compile(
    r"^\s+(\d+)\s+\.\.\s+(\d+)\s+(\w+)(?:\s+(\S+)\s+(\d+))?\s*$")


def read_layout(path):
    """{partition: [(offset_in_super, offset_in_image, nbytes), ...]}"""
    proc = subprocess.run(["lpdump", path], capture_output=True, text=True)
    if proc.returncode != 0:
        hint = ""
        with open(path, "rb") as handle:
            if handle.read(4) == SIMDUMP_MAGIC:
                hint = ("\nthis is an Android sparse image and lpdump reads only linear "
                        "ones:\n  simg2img %s %s.raw" % (path, path))
        raise SystemExit("lpdump exited %d on %s: %s\n%s"
                         % (proc.returncode, path, hint,
                            "\n".join((proc.stderr or proc.stdout)
                                      .strip().splitlines()[-4:])))
    rows, blocks, name, in_parts = {}, {}, None, False
    for line in proc.stdout.splitlines():
        if line and not line[0].isspace():
            # a section header: the per-partition blocks only count inside
            # "Partition table:", or "Name: main_a" of the group table reads as one
            in_parts = line.startswith("Partition table")
            name = None
        found = LAYOUT_ROW.match(line)
        if found:
            device, first, _last, part, sectors = found.groups()
            rows.setdefault(part, []).append(
                [int(first) * SECTOR, 0, int(sectors) * SECTOR, device])
            continue
        found = BLOCK_NAME.match(line)
        if found and in_parts:
            name = found.group(1)
            blocks.setdefault(name, [])
            continue
        found = BLOCK_EXTENT.match(line)
        if found and name is not None and found.group(3) == "linear":
            target_first, target_last, _kind, device, at = found.groups()
            blocks[name].append(
                [int(at) * SECTOR, int(target_first) * SECTOR,
                 (int(target_last) - int(target_first) + 1) * SECTOR, device])
    layout = rows or blocks
    if not layout:
        raise SystemExit("lpdump gave no partition layout for %s\n%s"
                         % (path, "\n".join(proc.stdout.splitlines()[:8])))
    for segs in layout.values():
        segs.sort()
        at = 0
        for seg in segs:      # lpdump's layout rows do not say where in the partition
            seg[1] = at       # an extent starts, so chain them: they are contiguous
            at += seg[2]
    return layout


def compare(dst, src, img_off, super_off, size):
    """Compare size bytes of src at img_off against dst at super_off.

    Returns None when they match and the offset of the first differing byte inside
    the source image when they do not, so the message can point at a place.
    """
    with open(src, "rb") as ref:
        ref.seek(img_off)
        dst.seek(super_off)
        done = 0
        while done < size:
            n = min(CHUNK, size - done)
            mine, theirs = ref.read(n), dst.read(n)
            if len(mine) != n or len(theirs) != n:
                return done + min(len(mine), len(theirs))
            if mine != theirs:
                for offset in range(n):
                    if mine[offset] != theirs[offset]:
                        return done + offset
            done += n
    return None


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: %s super-check.img extracted"
                         % os.path.basename(sys.argv[0]))
    built, src_dir = sys.argv[1], sys.argv[2].rstrip("/")
    if not os.path.isfile(built):
        raise SystemExit("no such file: " + built)
    if not os.path.isdir(src_dir):
        raise SystemExit("not a directory: " + src_dir)

    layout = read_layout(built)
    bad = filled = 0
    with open(built, "rb") as dst:
        for name, segs in sorted(layout.items()):
            if not segs:
                print("  %-15s empty in super" % name)
                continue
            filled += 1
            src = os.path.join(src_dir, re.sub(r"_[ab]$", "", name) + ".img")
            total = sum(seg[2] for seg in segs)
            have = os.path.getsize(src) if os.path.isfile(src) else None
            if have is None:
                print("  %-15s MISSING  %d bytes in super, no %s"
                      % (name, total, src))
                bad += 1
                continue
            if have != total:
                print("  %-15s SIZE  %d bytes in super, %d in %s"
                      % (name, total, have, src))
                bad += 1
                continue
            failed = None
            for index, (super_off, img_off, size, device) in enumerate(segs):
                if device != "super":
                    failed = "reads its data from a device named %r" % device
                    break
                gap = compare(dst, src, img_off, super_off, size)
                if gap is not None:
                    failed = ("byte %d of %s is not what super holds at sector %d"
                              % (img_off + gap, src, (super_off + gap) // SECTOR))
                    break
            if failed is None:
                more = "" if len(segs) == 1 else ", %d extents" % len(segs)
                print("  %-15s OK  %d bytes at sector %d%s"
                      % (name, total, segs[0][0] // SECTOR, more))
            else:
                print("  %-15s DIFFERS  %s" % (name, failed))
                bad += 1
    print("%d partitions hold data, %d bad" % (filled, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

