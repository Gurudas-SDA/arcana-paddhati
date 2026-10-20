// svgo for the layered SVG masters (V20c, Vraja Lila msg 5658): the layer ids and groups are the data — never
// renamed, merged or collapsed; curves kept as curves (no arcs / straightening), 3 decimals: renders like the
// original (s61: mean |Δ| ≤ 0.1 / 255). Run: npx svgo@4.1.0 --config scripts/svgo/paraphernalia.svgo.config.mjs -i <in> -o <out>
export default {
  multipass: true,
  floatPrecision: 3,
  plugins: [
    {
      name: "preset-default",
      params: {
        overrides: {
          cleanupIds: false,      // the layer ids _x31_ … _x31_8, Deities, plate are the data
          collapseGroups: false,  // groups 1-3 = object + its number
          inlineStyles: false,
          minifyStyles: true,
          mergePaths: false,      // never merge one layer's path with another
          removeHiddenElems: false,
          convertShapeToPath: false,
          convertPathData: { makeArcs: false, straightCurves: false, convertToQ: false, curveSmoothShorthands: false },
        },
      },
    },
  ],
};
