# Astrarium observation validation set

The bundled observation set has two targets:

- **M16 / Pillars of Creation:** Hubble WFC3/UVIS calibrated Level-4 FITS mosaics and six JWST NIRCam MAST filter previews. Both render on the same 200″ WCS grid. Metadata and filter provenance are in each observation folder.
- **HUDF12:** four calibrated, drizzled Hubble WFC3/IR FITS mosaics (F105W, F125W, F140W, F160W) rendered at the NASA-published HUDF center over 120″. The common intersection of positive WHT weight maps covers 80.8% of that square; areas without four-band coverage are masked to black. An independent NASA/ESA 2014 composite is included for visual comparison.

## Validation checks

1. Select each target and compare the displayed center and field against `observations/validation-set.json`.
2. Compare filter morphology and source placement after WCS projection. M16 Hubble and Webb must share the same celestial center and angular scale.
3. For HUDF, compare galaxy positions, shapes, and relative large-scale colors to the included NASA reference. Do not require identical color, brightness, or depth: the reconstruction uses four near-infrared filters, while the NASA reference combines 13 ultraviolet, visible, and infrared filters from four instruments.
4. Confirm that individual filter views retain the structures in their source planes and that no synthetic stars or nebula are introduced in telescope-data mode.
5. Treat the `common_coverage_fraction` in each generated metadata file as the valid pixel mask; pixels outside the source mosaic are not observed data.

## Sources

- [MAST HUDF12 products and processing](https://archive.stsci.edu/prepds/hudf12/)
- [NASA Hubble Ultra Deep Field 2014 reference and color mapping](https://science.nasa.gov/asset/hubble/hubble-ultra-deep-field-2014/)
- [MAST Hubble Heritage M16 products](https://archive.stsci.edu/prepds/heritage/m16/)
- [NASA Webb Pillars observation](https://science.nasa.gov/asset/webb/pillars-of-creation-nircam-image/)
