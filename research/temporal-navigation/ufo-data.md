# Astrarium UAP observation data

The projector consumes `player/app/src/main/assets/sky/ufo-sightings.json` as
an array of observation records. It does not download or scrape sighting
websites. The bundled Colorado pair is synthetic, supplied only to exercise
the observation and triangulation display.

## Import a redistributable CSV

Use [`scripts/import_ufo_sightings.py`](../scripts/import_ufo_sightings.py) with
a CSV containing these required columns:

```text
id,observedAtUtc,latitudeDeg,longitudeDeg
```

Optional columns are `label`, `timeUncertaintySec`, `observerAltitudeKm`,
`azimuthDeg`, `elevationDeg`, `angularUncertaintyDeg`, `rangeKm`,
`rangeUncertaintyKm`, and `eventId`.
Timestamps must include `Z` or an explicit UTC offset. Azimuth is clockwise
from north in degrees; elevation is degrees above the local horizon. Direction
and angular precision must come from the source or a documented measurement
process. `timeUncertaintySec` is required for triangulation and must reflect
the recorded timestamp's actual precision; observations are combined only when
their time intervals overlap. `observerAltitudeKm` is height above the WGS-84
ellipsoid. Set Astrarium's own site elevation in the dashboard's sound/location
settings to reproject solved positions from the correct horizon origin.
When a source omits observer elevation, the solver assumes zero ellipsoid height
and labels the derived position accordingly.
`eventId` groups independent observations of one event; do not group
reports solely because their dates or descriptions look similar.

Example:

```sh
python3 scripts/import_ufo_sightings.py observations.csv \
  player/app/src/main/assets/sky/ufo-sightings.json \
  --source 'Licensed observation archive' \
  --source-url 'https://example.org/dataset' \
  --source-rights 'CC BY 4.0, verified 2026-10-16' \
  --redistribution-permitted --append
```

The explicit `--redistribution-permitted` flag is an operator attestation, not
a legal review. The importer stores that attestation and the rights reference
with every row. Without the flag, it refuses to write. It does not accept
NUFORC exports under NUFORC's current terms, which prohibit scraping and
redistributing collections without express written permission. Obtain that
permission first if using NUFORC data.

The [National Archives UAP metadata guidance](https://www.archives.gov/records-mgmt/uap-guidance)
defines archival document fields such as record-creation date and city/state
location. Those fields help find historical source documents, but they are not
necessarily the observation timestamp or a measured sky bearing required to
reconstruct a craft position. Astrarium does not turn document metadata into a
fabricated sightline.

## Source candidate: GEIPAN

GEIPAN's [official CSV announcement](https://www.cnes-geipan.fr/fr/node/15)
describes downloadable case-level and testimony/observation-level CSV files
intended for studies. It says witness coordinates are rounded to 0.1 degree
(about 10 km in metropolitan France), some fields are omitted or filtered for
confidentiality, and complete narratives were still under review. Its
[technical questionnaire](https://www.geipan.fr/sites/default/files/Questionnaires%20techniques-R.pdf)
asks for initial/final direction and elevation, and a rough object distance;
that does not prove those values are present in the public CSV export for every
record. Some individual published cases report more detailed observations; for
example, the [La Turballe case](https://www.cnes-geipan.fr/fr/cas/2024-12-51617)
describes a witness recording GPS coordinates and azimuth. GEIPAN classified
that event as a bolide, so it is a useful resolved comparison case, not an
unidentified-craft record. Case narratives and attachments are not a substitute
for a documented bulk-data schema or reuse license. The CSV download
announcement does not state a redistribution license, so verify reuse rights
with CNES before packaging the CSV or derived records. Even when a bearing is
available, the bulk export's roughly 10 km observer-location rounding must be
carried into any 3D estimate.

## Timeline-only source: UAPDrop

[UAPDrop's open dataset](https://www.uapdrop.com/data.html) states that its
compiled records are CC BY 4.0 and include observed time, geocoded coordinates,
coordinate precision, and links to source records. Its documented record
contract does not list observer azimuth or elevation, so these rows can support
a sourced report timeline but cannot locate the observed craft in 3D. Preserve
UAPDrop attribution and each originating `source_url` if using it for that
timeline; do not treat its observer coordinates as craft positions.

## Archival source requiring case-by-case extraction: Project Blue Book

The [U.S. National Archives Project BLUE BOOK collection](https://www.archives.gov/research/military/air-force/ufos)
provides historical case files rather than a normalized sightline dataset.
Some scanned reports contain observer locations, observation times, azimuths,
and elevations, but completeness and measurement quality vary by case. Treat
each extracted observation as a separately sourced record, preserve its NARA
catalog reference, and only group reports when the source establishes that
they describe the same event. Do not infer a range from a single bearing.

Rows with location and time but no azimuth/elevation are retained as records,
but cannot be placed on the sky. A single bearing is rendered only near its
observer and does not produce a range estimate. A supplied range can be
combined with a bearing to plot a sourced range-based point. Multiple
bearings sharing an `eventId` can produce a least-squares closest point only
when their reported time-uncertainty intervals overlap, the directions each
have reported angular uncertainty, and their span is no more than ten minutes.
Astrarium displays its altitude and ray miss residual as a derived estimate.
Missing precision stays missing and prevents triangulation.

The current propagation treats a solved point as stationary during the
observation interval. It uses WGS-84 Earth-fixed coordinates and does not estimate a moving
trajectory, velocity, object size, or probability distribution. The displayed
RMS miss distance is a geometric consistency measure, not a confidence
interval. A serious trajectory reconstruction needs synchronized observations,
calibrated angular errors, observer elevation, Earth orientation, and a motion
model fitted to multiple timed observations.
