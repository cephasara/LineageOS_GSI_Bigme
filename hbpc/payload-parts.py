#!/usr/bin/env python3
"""Report what a Bigme A/B OTA payload writes, and pull images out of it.

The payload puts its headers at the beginning:

    'CrAU' | BE u64 format version | BE u64 manifest size | BE u32 signature size
    | DeltaArchiveManifest | payload signature | blob data

The manifest is the AOSP `update_metadata.proto` message, so this needs the
generated module that `payload_dumper` ships:

    python3 -m venv .venv && .venv/bin/pip install payload_dumper
    ../hbpc/payload-parts.py payload.bin                 # report
    ../hbpc/payload-parts.py payload.bin --list          # partition names
    ../hbpc/payload-parts.py payload.bin OUTDIR boot dtbo  # extract
    ../hbpc/payload-parts.py payload.bin --lpmake          # super.img build command

`--lpmake` prints the lpmake command that assembles the dynamic partitions already
extracted into --images (default `extracted`) into one super image (--out, default
`super.img`) for the slot --slot (default `_a`). The sizes and the group name come
from the manifest; the manifest's PartitionInfo carries only size and hash, so the
logical-partition attributes are emitted as `none` - compare with `lpdump` over the
factory super and pass `readonly` if that one says so. The geometry defaults to this
phone's 12 GiB super with 64 KiB metadata in 3 slots, overridable with --super-size,
--metadata-size and --metadata-slots. See STOCK-CROSSFLASH-INFO.md; the install steps in
STOCK-CROSSFLASH-INSTALL.md do not need it, they let fastbootd resize each partition.

Extraction handles REPLACE, REPLACE_BZ and REPLACE_XZ, checks every operation
hash and the rebuilt image hash, and so covers what Bigme's packages use
(`vabc_enabled` is false in the 3.4.6 package). Ops that reference a source
partition (BSDIFF, PUFFDIFF, SOURCE_COPY) are refused: those need the old
image and are not in a full package.
"""
import bz2
import hashlib
import lzma
import os
import sys

try:
    from payload_dumper.dumper import Dumper
    from payload_dumper import update_metadata_pb2 as um
except ImportError:
    sys.exit("needs payload_dumper: python3 -m venv .venv && .venv/bin/pip install "
             "payload_dumper, then run this with that interpreter")


def report(dam, block_size, data_offset):
    print(f"block_size={block_size} minor_version={dam.minor_version} "
          f"partial_update={dam.partial_update} data_offset={data_offset}")
    print(f"partitions written: {len(dam.partitions)}")
    total_ops = total_data = total_bytes = 0
    for part in dam.partitions:
        ops = part.operations
        data = sum(op.data_length for op in ops)
        new = part.new_partition_info
        kinds = {}
        for op in ops:
            key = um.InstallOperation.Type.Name(op.type)
            kinds[key] = kinds.get(key, 0) + 1
        kinds_text = " ".join(f"{k}x{v}" for k, v in sorted(kinds.items()))
        total_ops += len(ops)
        total_data += data
        total_bytes += new.size
        old = (f"old={part.old_partition_info.size:>13,}"
               if part.HasField("old_partition_info") else " " * 18)
        print(f"  {part.partition_name:<16} new={new.size:>13,} {old} "
              f"ops={len(ops):>5} data={data:>13,} [{kinds_text}]")
        if new.hash:
            print(f"  {'':<16} sha256={new.hash.hex()}")
    print(f"TOTAL new={total_bytes:,} bytes  ops={total_ops}  "
          f"payload data={total_data:,}")
    dpm = dam.dynamic_partition_metadata
    print(f"virtual-A/B: snapshot={dpm.snapshot_enabled} vabc={dpm.vabc_enabled} "
          f"compression={dpm.vabc_compression_param!r} cow_version={dpm.cow_version}")
    for group in dpm.groups:
        print(f"  group {group.name} size={group.size:,} "
              f"members={list(group.partition_names)}")


def extract(dumper, names, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for part in dumper.dam.partitions:
        if part.partition_name not in names:
            continue
        path = os.path.join(out_dir, f"{part.partition_name}.img")
        written = 0
        digest = hashlib.sha256()
        with open(path, "wb") as out:
            for op in part.operations:
                kind = um.InstallOperation.Type.Name(op.type)
                if kind not in ("REPLACE", "REPLACE_BZ", "REPLACE_XZ"):
                    raise SystemExit(f"{part.partition_name}: unsupported op {kind}; "
                                     "it needs the partition it patches")
                dumper.payloadfile.seek(dumper.data_offset + op.data_offset)
                blob = dumper.payloadfile.read(op.data_length)
                if op.data_sha256_hash:
                    assert hashlib.sha256(blob).digest() == op.data_sha256_hash, \
                        f"{part.partition_name}: operation hash mismatch"
                if kind == "REPLACE_BZ":
                    blob = bz2.decompress(blob)
                elif kind == "REPLACE_XZ":
                    blob = lzma.decompress(blob)
                digest.update(blob)
                out.write(blob)
                written += len(blob)
        want = part.new_partition_info.hash.hex()
        got = digest.hexdigest()
        state = "HASH OK" if got == want else f"HASH MISMATCH {got}"
        print(f"  {part.partition_name:<16} {written:>13,} bytes  {state}  {path}")


LPMAKE_DEFAULTS = {
    # The HiBreak Pro Color geometry, from lpdump over the phone's super and over
    # the factory super.img: 12 GiB, 64 KiB metadata, 3 metadata slots.
    "slot": "_a",
    "out": "super.img",
    "images": "extracted",
    "super_size": "12884901888",
    "metadata_size": "65536",
    "metadata_slots": "3",
    "sparse": True,
}

LPMAKE_FLAGS = {
    "--slot": "slot",
    "--out": "out",
    "--images": "images",
    "--super-size": "super_size",
    "--metadata-size": "metadata_size",
    "--metadata-slots": "metadata_slots",
}


def parse_lpmake_opts(args):
    opts = dict(LPMAKE_DEFAULTS)
    i = 0
    while i < len(args):
        flag = args[i]
        if flag == "--sparse":
            opts["sparse"] = True
        elif flag == "--raw":
            opts["sparse"] = False
        elif flag in LPMAKE_FLAGS:
            if i + 1 >= len(args):
                sys.exit(f"{flag} needs a value")
            opts[LPMAKE_FLAGS[flag]] = args[i + 1]
            i += 1
        else:
            sys.exit(f"unknown --lpmake option {flag}\n\n{__doc__}")
        i += 1
    return opts


def lpmake_script(dam, opts):
    """Print the lpmake command that assembles the payload's dynamic partitions
    into one super image, taking every size and attribute from the manifest.

    The slot suffix defaults to _a, the slot this phone boots; the other slot is
    declared empty, as the factory super leaves it.
    """
    dpm = dam.dynamic_partition_metadata
    if not dpm.groups:
        raise SystemExit("the payload declares no dynamic-partition groups, so there "
                         "is no super layout to build")
    slot = opts["slot"]
    other = slot[:-1] + ("b" if slot.endswith("a") else "a") if slot else ""
    images = opts["images"].rstrip("/")
    written = {p.partition_name: p for p in dam.partitions}
    group_of = {name: group.name for group in dpm.groups
                for name in group.partition_names}
    members = [name for group in dpm.groups for name in group.partition_names]
    missing = sorted(n for n in members
                     if n not in written or not os.path.isfile(f"{images}/{n}.img"))
    if missing:
        raise SystemExit(
            "no image for " + " ".join(missing) + f" in {images}\n"
            f"  extract them first: payload-parts.py <payload.bin> {images} "
            + " ".join(missing))

    argv = ["lpmake"]
    if opts["sparse"]:
        argv.append("--sparse")
    argv += [f"--block-size {dam.block_size}",
             f"--metadata-size {opts['metadata_size']}",
             f"--metadata-slots {opts['metadata_slots']}",
             "--super-name super",
             f"--device super:{opts['super_size']}"]
    if dpm.snapshot_enabled:
        argv.append("--virtual-ab")
    for group in dpm.groups:
        argv += [f"--group {group.name}{slot}:{group.size}",
                 f"--group {group.name}{other}:{group.size}"]
    used = {}
    for name in members:
        part = written[name]
        group = group_of[name]
        info = part.new_partition_info
        size = info.size
        # The manifest PartitionInfo message carries only size and hash, so the LP
        # attributes are unknown here: lpdump the factory super and pass `readonly`
        # if its Attributes: line says so.
        attr = "readonly" if getattr(info, "attributes", 0) & 1 else "none"
        used[group] = used.get(group, 0) + size
        argv += [f"--partition {name}{slot}:{attr}:{size}:{group}{slot}",
                 f"--image {name}{slot}={images}/{name}.img",
                 f"--partition {name}{other}:none:0:{group}{other}"]
    print(" \\\n  ".join(argv) + f" \\\n  --output {opts['out']}")
    for group in dpm.groups:
        got, limit = used.get(group.name, 0), group.size
        state = "fits" if got <= limit else "DOES NOT FIT"
        print(f"# group {group.name}{slot}: {got:,} of {limit:,} bytes, "
              f"{limit - got:,} spare - {state}")
    print(f"# check it: simg2img {opts['out']} check.img && lpdump check.img"
          "  (lpdump cannot read a sparse file)")


def main():
    argv = sys.argv[1:]
    if not argv or any(a in ("-h", "--help") for a in argv):
        print(__doc__)
        return
    if argv[0].startswith("-"):
        sys.exit(f"unknown option {argv[0]}\n\n{__doc__}")
    dumper = Dumper(open(argv[0], "rb"), out=None)
    rest = argv[1:]
    if rest and rest[0] == "--lpmake":
        lpmake_script(dumper.dam, parse_lpmake_opts(rest[1:]))
    elif not rest:
        report(dumper.dam, dumper.block_size, dumper.data_offset)
    elif rest == ["--list"]:
        print(" ".join(p.partition_name for p in dumper.dam.partitions))
    elif rest[0].startswith("-"):
        sys.exit(f"unknown option {rest[0]}\n\n{__doc__}")
    else:
        extract(dumper, set(rest[1:]), rest[0])


if __name__ == "__main__":
    main()
