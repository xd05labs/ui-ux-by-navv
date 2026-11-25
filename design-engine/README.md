# Design engine

Palettes are in `palettes/catalog.json`; visual recipes are in `design-library/catalog.json`. `appforge/design.py` generates light and dark semantic tokens and shared CSS. Primary, secondary, accent, background, surface, border, text, hover, focus, success, warning, error and disabled roles are derived centrally.

Relative luminance uses sRGB linearization. Foreground colors move toward black or white until text contrast reaches 4.5:1; focus/control boundaries target 3:1. On-primary chooses the better contrasting black/white foreground. Reports list measured pairs in both modes. Original branding colors remain config inputs; accessible rendered colors may differ.

These checks cover token pairs, not every composition. Test actual rendered states, transparent surfaces, browser zoom, forced colors, keyboard focus, reduced motion and assistive technology. Shadow-only affordances are insufficient. Avoid making disabled text the only way to explain an unavailable action.
