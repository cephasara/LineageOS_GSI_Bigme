# Black/white Launcher themed icon colors

HiBreak overrides the themed icon color resources in the Launcher product overlay.
This keeps the change scoped to Launcher and leaves the system accent palette and
other iconloader consumers untouched.

| Role | Light | Dark |
| --- | --- | --- |
| Icon foreground | Opaque black | Opaque white |
| Icon background | Opaque white | Opaque black |
| Adaptive fallback background | Opaque white | Opaque black |
| Themed profile badge foreground/background | Black/white | Black/white |

The badge pair preserves the upstream dark-mode inverse polarity relative to the
main icon. Overrides cover default, night, v31 and night-v31 resources so the
Android 12+ accent references cannot take precedence. The static drawer uses its
existing light context and therefore shows black artwork on white icon backgrounds.

ThemedIconDelegate, themed dynamic clocks and generated monochrome icons use these
roles. In the examined BP4A build, forceMonochromeAppIcons is enabled and
forceMonochromeAppIconsAdaptColors is disabled; generated icons use the same pair.
Review that flag when upgrading the release, since its enabled path can adapt colors.

The existing 1dp black contour and themed-shadow clipping are retained. Theme-icon
preferences, ordinary icons, badges that are not themed, generated alpha masks,
antialiasing, disabled alpha and application identity are unchanged. This changes
paint colors, not bitmap pixels into a binary black/white raster.

The normal-image verifier checks all five roles for the packaged default/night
Launcher product overlay. The appearance on the panel needs a device check.
