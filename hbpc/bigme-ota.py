#!/usr/bin/env python3
"""Query Bigme's stock firmware (OTA) and system-app update servers.

Metadata only: this script never downloads or installs firmware or apps.
It needs Python 3 and the openssl executable; no pip packages.
See BIGME-OTA.md next to this script for the protocol and examples.

OTA protocol and key reference: marek-vybiral/bigme-ota-client
(https://github.com/marek-vybiral/bigme-ota-client, Unlicense), commit db50aa6.
The keys match the official B651 CN Settings 2.8.7 client. The response key
is distributed inside that client; it is not a device secret.
"""
import argparse
import base64
import datetime
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

OTA_SERVERS = {
    "cn": "http://ereader.bigme.vip:8090/json/osupgrade.action",
    "usa": "http://usa.bigme.vip:8090/json/osupgrade.action",
}
# The stock app updater uses this fixed endpoint regardless of the server choice.
APPS_URL = "http://ereader.bigme.vip:8081/xrzApp"
USER_AGENT = "okhttp/4.9.1"
PUB_DER_B64 = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC40cQNQjd9e4YBrVaWXk1eyfcRJEbqsLm6T2/XF6ZpXeBz3JkzSQ1jwyRQ2HGCNJcTW/waAWuMjhu5sHZTNjtI8TzZYNS7P/ZuSkwv99ax5sZTIsFb9dspVoj/W6eQ9i5P493LEi5It4fLofocbBO65aAAi0SHmQ3zuRCMbkbtkQIDAQAB'
PRIV_DER_B64 = 'MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAM6xVSw56KrrA/jbocCpk2w3lIrlKheymyC2mg+Iq2gCG4QJd101VSlNbo+mNi/eaHzHAAnlh2o5rMgbww7lNb25FIrVa/XhzzfYxFatFNaLhkS8XH9AyFce0/v0SJ9TRr4+OeHsupPJPeCoguREZeMTA+LhJfs3iy+KKF3JyldlAgMBAAECgYBok/LbQKWHLQfCdyXdPC96FpkSuaZVfSneIGXMrELFiiNv5/Y788sV7bad+eP6zlYho/JSD483YN0aFmnX9IL+hO9LzSyEU8Ja1dvNhiDP7OX4y1M8V+fxFrOgBU4A7Hin8DPnAWvFGqfaYGwH7YfX0QVUK76hRO/7uOQRloB5lQJBAPdKIC5gr41mNSZTyNQsDNvAHnRNVgqovDqw2MR95tCvEII6FXpEmgrfpRr+puXpxJrkWJzRq7PnMP7llD8mSJsCQQDV+SJ4mIXbzBTgeqREj0cBipTbsCQhXHUEirlRVDoECxZgoTjubb3YfIjsnukyev8z56KnrzXRASqc5VYMS9//AkAlanXMDp0BTAGmtu6gC7o2Va9F8Z2fJ0CzsKZbtKED2jkpOxic01xrYMNefkFKcEBrHzm5IJBWPBjRuHLhyy0ZAkBkhg/IwjcY5M7mCxgDUaCVO8rlTuIafjpHcPjRGZXL8n2H1hZOBWaMPy2ApMN/wMMGWotS5gCNeVPQs/lx+293AkEAzHcNIEXF9q+EAi8tQPvDsn7mZZVk1IIkGIohgcB/Q94Hyxjb0dL9LnkCP3cMgAkfNsICNmITtJE0ikwxWVoQJQ=='


def rsa_blocks(data, key_der, decrypt, work_dir):
    """RSA-1024 PKCS#1 v1.5: request chunks 117, response blocks exactly 128."""
    size = 128 if decrypt else 117
    if decrypt and (not data or len(data) % size):
        raise ValueError("RSA response length must be a nonzero multiple of 128")
    with tempfile.TemporaryDirectory(prefix="rsa-", dir=work_dir) as directory:
        key = Path(directory) / "client-key.der"
        key.write_bytes(key_der)
        command = ["openssl", "pkeyutl", "-decrypt" if decrypt else "-encrypt",
                   "-inkey", str(key), "-keyform", "DER",
                   "-pkeyopt", "rsa_padding_mode:pkcs1"]
        if not decrypt:
            command.append("-pubin")
        output = bytearray()
        for start in range(0, len(data), size):
            result = subprocess.run(command, input=data[start:start + size],
                                    capture_output=True, timeout=15)
            if result.returncode:
                raise ValueError("OpenSSL RSA operation failed (invalid key or ciphertext)")
            output.extend(result.stdout)
        return bytes(output)


def encode_request(fields, work_dir):
    body = json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode()
    return base64.b64encode(rsa_blocks(body, base64.b64decode(PUB_DER_B64),
                                       False, work_dir))


def decode_response(raw, work_dir):
    encoded = b"".join(raw.split())
    encoded += b"=" * (-len(encoded) % 4)
    encrypted = base64.b64decode(encoded, validate=True)
    plain = rsa_blocks(encrypted, base64.b64decode(PRIV_DER_B64), True, work_dir)
    result = json.loads(plain.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object in the decoded response")
    return result


def decode_apps_response(raw):
    result = json.loads(raw.decode("utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object in the app-update response")
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post(url, body, content_type, lang, args):
    if args.transport == "host":
        headers = {"Content-Type": content_type, "lang": lang, "User-Agent": USER_AGENT}
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        # Keep identity-bearing requests at the explicitly selected endpoint.
        opener = urllib.request.build_opener(NoRedirect())
        try:
            with opener.open(request, timeout=args.timeout) as response:
                return response.read(), {"http_status": response.status}
        except urllib.error.HTTPError as error:
            return error.read(), {"http_status": error.code}
    command = [args.adb]
    if args.adb_serial:
        command += ["-s", args.adb_serial]
    # No remote shell quoting: exec-out curl reads the request from stdin,
    # so the body is never written to the phone's storage.
    command += ["exec-out", "curl", "-sS", "--connect-timeout", str(args.timeout),
                "--max-time", str(args.timeout),
                "-H", "Content-Type:" + content_type.replace(" ", ""),
                "-H", "lang:" + lang, "-A", USER_AGENT,
                "--data-binary", "@-", url]
    result = subprocess.run(command, input=body, capture_output=True,
                            timeout=args.timeout + 10)
    if result.returncode:
        raise RuntimeError(f"adb/curl exited {result.returncode}; check the device connection and curl")
    return result.stdout, {"http_status": None, "note": "ADB transport preserves the raw body only"}


def write_new(path, data):
    with path.open("xb") as file:
        file.write(data)


def write_json(path, value):
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    write_new(path, rendered.encode())
    return rendered


def read_sn(args):
    if args.sn_file:
        sn = args.sn_file.read_text().strip()
    else:
        sn = getpass.getpass("Device SN (hidden): ").strip()
    if not sn or any(c in sn for c in "\r\n"):
        raise ValueError("SN must be one nonempty line")
    return sn


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", choices=["ota", "apps", "all"], default="ota",
                        help="ota: firmware update (default); apps: system-app update list; all: both")
    parser.add_argument("--server", choices=["cn", "usa", "both"], default="both",
                        help="OTA server(s); the app list always uses ereader.bigme.vip:8081")
    parser.add_argument("--os-name", help="stock model/channel, for example 'B651 CN' (required to query)")
    parser.add_argument("--os-version", help="stock OS version, for example '3.3.0'; not a GSI version (required to query)")
    parser.add_argument("--product-name",
                        help="stock ro.build.versionProduct, for example 'HiBreak pro' (required for --query apps/all)")
    parser.add_argument("--sn-file", type=Path, help="file containing only your device SN; otherwise a hidden prompt")
    parser.add_argument("--lang", help="lang header; default zh-CN for OTA and zh_CN for the app list")
    parser.add_argument("--ota-fail-count", type=int, help="optional OTA client field; omitted by default")
    parser.add_argument("--transport", choices=["host", "adb"], default="host",
                        help="host: this computer's network; adb: curl on the phone over adb exec-out")
    parser.add_argument("--adb", default="adb", help="adb executable for the adb transport")
    parser.add_argument("--adb-serial", help="adb -s device selector if several devices are connected")
    parser.add_argument("--timeout", type=int, default=25, help="seconds per request (default 25)")
    parser.add_argument("--output-dir", type=Path, help="new output directory; default ./bigme-ota-<UTC time>")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-only", action="store_true",
                      help="write the request files without sending anything")
    mode.add_argument("--decode-response", type=Path, metavar="FILE",
                      help="decrypt a saved raw OTA response; no network and no SN needed")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0 or (args.ota_fail_count is not None and args.ota_fail_count < 0):
        parser.error("timeout must be positive and ota-fail-count nonnegative")
    if args.lang is not None and any(c in args.lang for c in "\r\n"):
        parser.error("lang must not contain line breaks")
    want_ota = args.query in ("ota", "all")
    want_apps = args.query in ("apps", "all")
    if not args.decode_response:
        missing = [flag for flag, value in (("--os-name", args.os_name), ("--os-version", args.os_version))
                   if not value]
        if want_apps and not args.product_name:
            missing.append("--product-name")
        if missing:
            parser.error("missing " + ", ".join(missing))
    os.umask(0o077)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = args.output_dir or Path("bigme-ota-" + timestamp)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)

    if args.decode_response:
        decoded = decode_response(args.decode_response.read_bytes(), output)
        print(write_json(output / "response.json", decoded), end="")
        print(f"Saved: {output}", file=sys.stderr)
        return 0

    sn = read_sn(args)
    info = {"time_utc": timestamp, "transport": args.transport}
    ota_names = []
    if want_ota:
        fields = {"sn": sn, "osName": args.os_name, "osVersion": args.os_version}
        if args.ota_fail_count is not None:
            fields["otaFailCount"] = args.ota_fail_count
        ota_body = encode_request(fields, output)
        write_new(output / "request.b64", ota_body)
        ota_names = list(OTA_SERVERS) if args.server == "both" else [args.server]
        info["ota"] = {"request": {**fields, "sn": "<omitted>"}, "lang": args.lang or "zh-CN",
                       "endpoints": {name: OTA_SERVERS[name] for name in ota_names}}
    if want_apps:
        app_fields = {"deviceSn": sn, "productModel": args.os_name,
                      "versionCode": args.os_version, "versionName": args.product_name}
        # Plain JSON containing the SN: kept in memory only, never written out.
        apps_body = json.dumps(app_fields, ensure_ascii=False, separators=(",", ":")).encode()
        info["apps"] = {"request": {**app_fields, "deviceSn": "<omitted>"},
                        "lang": args.lang or "zh_CN", "endpoint": APPS_URL}
    write_json(output / "request-info.json", info)
    print(f"Saved: {output}", file=sys.stderr)
    if args.prepare_only:
        return 0

    failed = False
    for name in ota_names:
        url = OTA_SERVERS[name]
        try:
            raw, status = post(url, ota_body, "application/json; charset=utf-8",
                               info["ota"]["lang"], args)
            write_new(output / f"{name}-response.b64", raw)
            write_json(output / f"{name}-transport.json", status)
            decoded = decode_response(raw, output)
            print(f"[ota {name}] {url}")
            print(write_json(output / f"{name}-response.json", decoded), end="")
            if status["http_status"] is not None and status["http_status"] >= 400:
                failed = True
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            failed = True
            print(f"ota {name}: {error}", file=sys.stderr)
    if want_apps:
        try:
            raw, status = post(APPS_URL, apps_body, "application/json; charset=UTF-8",
                               info["apps"]["lang"], args)
            write_new(output / "apps-response.raw", raw)
            write_json(output / "apps-transport.json", status)
            decoded = decode_apps_response(raw)
            print(f"[apps] {APPS_URL}")
            print(write_json(output / "apps-response.json", decoded), end="")
            if decoded.get("code") != 0 or (status["http_status"] is not None
                                            and status["http_status"] >= 400):
                failed = True
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            failed = True
            print(f"apps: {error}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, EOFError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
