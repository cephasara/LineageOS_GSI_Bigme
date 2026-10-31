# Changelog

Changes of the HiBreak Pro Color port that you notice on the phone. Images are on
[SourceForge](https://sourceforge.net/projects/lineageos-hibreakpro-color/).

## v23.2-20261031

Downloads: [https://sourceforge.net/projects/lineageos-hibreakpro-color/files/23.2/20261031/](https://sourceforge.net/projects/lineageos-hibreakpro-color/files/23.2/20261031/)

- GApps: [LineageOS-23.2-20261031-HBPC-GAPPS-EXT4-GSI.img.xz](https://sourceforge.net/projects/lineageos-hibreakpro-color/files/23.2/20261031/LineageOS-23.2-20261031-HBPC-GAPPS-EXT4-GSI.img.xz/download)
- Vanilla: [LineageOS-23.2-20261031-HBPC-VANILLA-EXT4-GSI.img.xz](https://sourceforge.net/projects/lineageos-hibreakpro-color/files/23.2/20261031/LineageOS-23.2-20261031-HBPC-VANILLA-EXT4-GSI.img.xz/download)

Changes since v23.2-20261024:

- **VoLTE (4G calling):** the MediaTek IMS service is now part of the image, so VoLTE
  works without installing anything, and 4G Calling is offered on every carrier.
  Wi-Fi Calling is not forced on. See [hbpc/MTK-VOLTE.md](hbpc/MTK-VOLTE.md).
- **Incoming VoLTE calls ring:** the IMS service is patched so incoming VoLTE calls
  reach the phone.
- **No 5G while on Wi-Fi:** while Wi-Fi is the default network the phone stays on LTE
  and returns to 5G when Wi-Fi goes away. This fixes incoming calls that were missed
  on 5G SA with Wi-Fi on. Can be turned off; see
  [hbpc/NR-OFF-ON-WIFI.md](hbpc/NR-OFF-ON-WIFI.md).
- **Incoming call screen for E-Ink:** a static white page with two buttons (Answer,
  Decline) instead of the swipe gesture, plain buttons for "Reject with message" and
  "Answer and end ongoing call", no animations. See [hbpc/DIALER.md](hbpc/DIALER.md).
- **TrebleApp IMS settings:** the IMS download button is hidden (the image already has
  the IMS service), and the 4G Calling switch no longer turns on Wi-Fi Calling.
- LineageOS 23.2 sources refreshed to the 2026-10-31 heads.
