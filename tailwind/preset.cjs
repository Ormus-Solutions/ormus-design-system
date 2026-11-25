/* Tailwind v3 preset for the Ormus design system.
   Every value is a var(--ormus-*) from tokens.css, so no hex lives here and
   the page needs tokens.css loaded. Tailwind v3 cannot apply an opacity
   modifier (bg-ormus-gold/50) to a var(), so use the hairline or a CSS rule
   for translucent colors.

   tailwind.config.js:
     module.exports = {
       presets: [require("@ormus/design-system/tailwind/preset.cjs")],
       content: ["./src/index.html", "./src/app.js"],
     };
   Tailwind v4 uses tailwind/theme.css instead. */
const v = (name) => `var(--ormus-${name})`;

module.exports = {
  theme: {
    extend: {
      colors: {
        ormus: {
          midnight: v("midnight"),
          deep: v("deep"),
          gold: v("gold"),
          "gold-bright": v("gold-bright"),
          ink: v("ink"),
          "ink-muted": v("ink-muted"),
          dim: v("dim"),
          hairline: v("hairline"),
          "on-gold": v("on-gold"),
          "code-bg": v("code-bg"),
          danger: v("danger"),
          "accent-rose": v("accent-rose"),
          "accent-teal": v("accent-teal"),
          "accent-leaf": v("accent-leaf"),
          "accent-ember": v("accent-ember"),
          "accent-sky": v("accent-sky"),
          "accent-iris": v("accent-iris"),
        },
      },
      fontFamily: {
        display: [v("font-display")],
        sans: [v("font-sans")],
        mono: [v("font-mono")],
      },
      borderRadius: {
        ormus: v("radius"),
        "ormus-container": v("radius-container"),
        "ormus-pill": v("radius-pill"),
      },
      transitionTimingFunction: {
        "ormus-reveal": v("ease-reveal"),
      },
    },
  },
};
