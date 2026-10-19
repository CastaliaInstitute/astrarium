interface Env {
  CATALOG: R2Bucket;
  STAR_REGISTRY: D1Database;
}

type StarNameProposal = {
  name: string;
  ra: number;
  dec: number;
  distanceLy?: number;
  proposer?: string;
  story?: string;
};

type BlackHoleNameProposal = StarNameProposal & {
  massSolar?: number;
  type?: string;
};

type TileKind = "space" | "shell" | "sky";

const allowedCoreFiles = new Set([
  "space.bin", "space_index.bin", "shell.bin", "shell_index.bin",
  "sky.bin", "sky_index.bin",
]);
const indexCache = new Map<string, Uint8Array>();
const indexCacheLimit = 8;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Cache-Control": "public, max-age=60",
    },
  });
}

function registryJson(body: unknown, status = 200): Response {
  const response = json(body, status);
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  headers.set("Cache-Control", "no-store");
  return new Response(response.body, { status, headers });
}

function validProposal(value: unknown): value is StarNameProposal {
  if (!value || typeof value !== "object") return false;
  const p = value as Partial<StarNameProposal>;
  return typeof p.name === "string" && p.name.trim().length >= 2 && p.name.trim().length <= 80
    && Number.isFinite(p.ra) && p.ra! >= 0 && p.ra! < 360
    && Number.isFinite(p.dec) && p.dec! >= -90 && p.dec! <= 90
    && (p.distanceLy === undefined || (Number.isFinite(p.distanceLy) && p.distanceLy! > 0))
    && (p.proposer === undefined || (typeof p.proposer === "string" && p.proposer.trim().length <= 100))
    && (p.story === undefined || (typeof p.story === "string" && p.story.trim().length <= 1000));
}

function validBlackHoleProposal(value: unknown): value is BlackHoleNameProposal {
  if (!validProposal(value)) return false;
  const p = value as Partial<BlackHoleNameProposal>;
  return (p.massSolar === undefined || (Number.isFinite(p.massSolar) && p.massSolar! > 0 && p.massSolar! <= 1e12))
    && (p.type === undefined || (typeof p.type === "string" && ["stellar", "intermediate", "supermassive", "candidate", "unknown"].includes(p.type)));
}

async function starRegistry(request: Request, env: Env): Promise<Response> {
  if (request.method === "GET") {
    const url = new URL(request.url);
    const status = url.searchParams.get("status") === "all" ? "all" : "approved";
    const result = status === "all"
      ? await env.STAR_REGISTRY.prepare("SELECT id, name, ra, dec, distance_ly AS distanceLy, proposer, story, status, created_at AS createdAt FROM star_name_proposals ORDER BY created_at DESC LIMIT 500").all()
      : await env.STAR_REGISTRY.prepare("SELECT id, name, ra, dec, distance_ly AS distanceLy, proposer, story, status, created_at AS createdAt FROM star_name_proposals WHERE status = 'approved' ORDER BY name COLLATE NOCASE LIMIT 500").all();
    return registryJson({ stars: result.results });
  }
  if (request.method !== "POST") return registryJson({ error: "method not allowed" }, 405);
  let body: unknown;
  try { body = await request.json(); } catch { return registryJson({ error: "invalid JSON" }, 400); }
  if (!validProposal(body)) return registryJson({ error: "provide a name, RA (0–<360°), declination (−90–90°), and optional valid details" }, 400);
  const p = body;
  const name = p.name.trim().replace(/\s+/g, " ");
  const existing = await env.STAR_REGISTRY.prepare("SELECT id FROM star_name_proposals WHERE lower(name) = lower(?) AND status != 'rejected' LIMIT 1").bind(name).first();
  if (existing) return registryJson({ error: "that name already has a registry entry or pending proposal" }, 409);
  const id = crypto.randomUUID();
  await env.STAR_REGISTRY.prepare("INSERT INTO star_name_proposals (id, name, ra, dec, distance_ly, proposer, story, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')")
    .bind(id, name, p.ra, p.dec, p.distanceLy ?? null, p.proposer?.trim() || null, p.story?.trim() || null).run();
  return registryJson({ id, status: "pending", message: "Proposal received for review." }, 201);
}

async function blackHoleRegistry(request: Request, env: Env): Promise<Response> {
  if (request.method === "GET") {
    const status = new URL(request.url).searchParams.get("status") === "all" ? "all" : "approved";
    const columns = "id, name, ra, dec, distance_ly AS distanceLy, mass_solar AS massSolar, object_type AS type, proposer, story, status, created_at AS createdAt";
    const result = status === "all"
      ? await env.STAR_REGISTRY.prepare(`SELECT ${columns} FROM black_hole_name_proposals ORDER BY created_at DESC LIMIT 500`).all()
      : await env.STAR_REGISTRY.prepare(`SELECT ${columns} FROM black_hole_name_proposals WHERE status = 'approved' ORDER BY name COLLATE NOCASE LIMIT 500`).all();
    return registryJson({ blackHoles: result.results });
  }
  if (request.method !== "POST") return registryJson({ error: "method not allowed" }, 405);
  let body: unknown;
  try { body = await request.json(); } catch { return registryJson({ error: "invalid JSON" }, 400); }
  if (!validBlackHoleProposal(body)) return registryJson({ error: "provide a name, valid sky coordinates, and valid optional distance, mass, and type" }, 400);
  const p = body;
  const name = p.name.trim().replace(/\s+/g, " ");
  const existing = await env.STAR_REGISTRY.prepare("SELECT id FROM black_hole_name_proposals WHERE lower(name) = lower(?) AND status != 'rejected' LIMIT 1").bind(name).first();
  if (existing) return registryJson({ error: "that name already has a registry entry or pending proposal" }, 409);
  const id = crypto.randomUUID();
  await env.STAR_REGISTRY.prepare("INSERT INTO black_hole_name_proposals (id, name, ra, dec, distance_ly, mass_solar, object_type, proposer, story, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')")
    .bind(id, name, p.ra, p.dec, p.distanceLy ?? null, p.massSolar ?? null, p.type ?? "unknown", p.proposer?.trim() || null, p.story?.trim() || null).run();
  return registryJson({ id, status: "pending", message: "Black hole naming proposal received for review." }, 201);
}

const terrainProducts = {
  dem: {
    service: "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer",
    format: "tiff",
    contentType: "image/tiff",
    extension: "tif",
  },
  imagery: {
    service: "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer",
    format: "png32",
    contentType: "image/png",
    extension: "png",
  },
} as const;

async function earthTerrain(request: Request, env: Env, productName: string): Promise<Response> {
  const product = terrainProducts[productName as keyof typeof terrainProducts];
  if (!product) return json({ error: "unknown terrain product" }, 404);
  const query = new URL(request.url).searchParams;
  const latitude = Number(query.get("lat"));
  const longitude = Number(query.get("lon"));
  const radiusM = Number(query.get("radiusM") || 1000);
  const size = Number(query.get("size") || 1024);
  if (!Number.isFinite(latitude) || latitude < -85 || latitude > 85
      || !Number.isFinite(longitude) || longitude < -180 || longitude > 180
      || ![250, 500, 1000, 2000, 5000, 10000].includes(radiusM)
      || ![256, 512, 1024].includes(size)) {
    return json({ error: "valid lat/lon, radiusM (250, 500, 1000, 2000, 5000, 10000), and size (256, 512, 1024) are required" }, 400);
  }

  // Quantize coordinates to keep one shared server copy for nearby requests.
  const lat = Math.round(latitude * 10000) / 10000;
  const lon = Math.round(longitude * 10000) / 10000;
  const key = `earth-terrain/v1/${productName}/${lat.toFixed(4)}/${lon.toFixed(4)}/${radiusM}/${size}.${product.extension}`;
  const stored = await env.CATALOG.get(key);
  if (stored) {
    const storedBounds = stored.customMetadata?.bbox || "";
    return new Response(request.method === "HEAD" ? null : stored.body, {
      headers: {
        "Content-Type": product.contentType,
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Expose-Headers": "X-Astrarium-Terrain-Bounds, X-Astrarium-Terrain-Cache, X-Astrarium-Terrain-Source",
        "Cache-Control": "public, max-age=86400, immutable",
        "X-Astrarium-Terrain-Cache": "hit",
        "X-Astrarium-Terrain-Bounds": storedBounds,
      },
    });
  }

  const latDelta = radiusM / 111320;
  const lonDelta = radiusM / (111320 * Math.max(Math.cos(latitude * Math.PI / 180), 0.01));
  const bbox = [lon - lonDelta, lat - latDelta, lon + lonDelta, lat + latDelta].join(",");
  const exportUrl = new URL(`${product.service}/exportImage`);
  exportUrl.search = new URLSearchParams({
    f: "json", bbox, bboxSR: "4326", imageSR: "4326", size: `${size},${size}`,
    format: product.format, pixelType: productName === "dem" ? "F32" : "U8",
    interpolation: "RSP_BilinearInterpolation", noData: "-9999",
  }).toString();
  const manifestResponse = await fetch(exportUrl);
  if (!manifestResponse.ok) return json({ error: "USGS terrain service unavailable" }, 502);
  const manifest = await manifestResponse.json() as { href?: string; error?: { message?: string } };
  if (!manifest.href) return json({ error: manifest.error?.message || "USGS has no terrain coverage for this location" }, 404);
  const assetResponse = await fetch(manifest.href);
  if (!assetResponse.ok) return json({ error: "USGS terrain download failed" }, 502);
  const bytes = await assetResponse.arrayBuffer();
  if (bytes.byteLength > 12 * 1024 * 1024) return json({ error: "terrain tile exceeded the storage limit" }, 502);
  await env.CATALOG.put(key, bytes, {
    httpMetadata: { contentType: product.contentType, cacheControl: "public, max-age=31536000, immutable" },
    customMetadata: { source: product.service, latitude: String(lat), longitude: String(lon), resolution: `${size}x${size}`, bbox },
  });
  return new Response(request.method === "HEAD" ? null : bytes, {
    headers: {
      "Content-Type": product.contentType,
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Expose-Headers": "X-Astrarium-Terrain-Bounds, X-Astrarium-Terrain-Cache, X-Astrarium-Terrain-Source",
      "Cache-Control": "public, max-age=86400, immutable",
      "X-Astrarium-Terrain-Cache": "stored",
      "X-Astrarium-Terrain-Source": product.service,
      "X-Astrarium-Terrain-Bounds": bbox,
    },
  });
}

function binary(body: BodyInit | null, size?: number, cacheSeconds = 86400): Response {
  const headers = new Headers({
    "Content-Type": "application/octet-stream",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Cache-Control": `public, max-age=${cacheSeconds}, immutable`,
  });
  if (size !== undefined) headers.set("Content-Length", String(size));
  return new Response(body, { headers });
}

async function indexBytes(env: Env, objectKey: string): Promise<Uint8Array | null> {
  const resident = indexCache.get(objectKey);
  if (resident) return resident;
  const object = await env.CATALOG.get(objectKey);
  if (!object) return null;
  const bytes = new Uint8Array(await object.arrayBuffer());
  if (bytes.byteLength % 16 !== 0) throw new Error(`bad tile index: ${objectKey}`);
  if (indexCache.size >= indexCacheLimit) indexCache.delete(indexCache.keys().next().value!);
  indexCache.set(objectKey, bytes);
  return bytes;
}

function lookup(index: Uint8Array, key: bigint): { offset: number; count: number } | null {
  const view = new DataView(index.buffer, index.byteOffset, index.byteLength);
  let lo = 0;
  let hi = index.byteLength / 16 - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >>> 1;
    const at = mid * 16;
    const found = view.getBigUint64(at, true);
    if (found < key) lo = mid + 1;
    else if (found > key) hi = mid - 1;
    else return { offset: view.getUint32(at + 8, true), count: view.getUint32(at + 12, true) };
  }
  return null;
}

function parseKey(value: string): bigint | null {
  if (!/^(?:0[xX][0-9a-fA-F]+|[0-9]+)$/.test(value)) return null;
  try {
    const key = BigInt(value);
    return key >= 0n && key <= 0xffffffffffffffffn ? key : null;
  } catch {
    return null;
  }
}

async function serveTile(env: Env, kind: TileKind, level: string, keyText: string): Promise<Response> {
  if (!/^L(?:[0-9]|1[01])$/.test(level)) return json({ error: "invalid level" }, 400);
  const key = parseKey(keyText);
  if (key === null) return json({ error: "invalid tile key" }, 400);
  const indexName = kind === "space" ? "space_index.bin" : `${kind}_index.bin`;
  const dataName = kind === "space" ? "space.bin" : `${kind}.bin`;
  const indexKey = `${level}/${indexName}`;
  const index = await indexBytes(env, indexKey);
  if (!index) return json({ error: "unknown tile" }, 404);
  const hit = lookup(index, key);
  if (!hit) return json({ error: "unknown tile" }, 404);
  const recordBytes = kind === "shell" ? 8 : 12;
  const object = await env.CATALOG.get(`${level}/${dataName}`, {
    range: { offset: hit.offset, length: hit.count * recordBytes },
  });
  if (!object) return json({ error: "catalog data missing" }, 502);
  return binary(object.body, hit.count * recordBytes);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, HEAD, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Max-Age": "86400",
    }});
    if (request.method !== "GET" && request.method !== "HEAD") return json({ error: "method not allowed" }, 405);

    const parts = new URL(request.url).pathname.split("/").filter(Boolean);
    if (parts[0] !== "api" || parts[1] !== "v1") return json({ error: "not found" }, 404);
    if (parts.length === 3 && parts[2] === "health") return json({ ok: true });
    if (parts.length === 3 && parts[2] === "star-names") return starRegistry(request, env);
    if (parts.length === 3 && parts[2] === "black-hole-names") return blackHoleRegistry(request, env);
    if (parts.length === 4 && parts[2] === "earth-terrain") return earthTerrain(request, env, parts[3]);

    if (parts.length === 3 && parts[2] === "manifest") {
      const object = await env.CATALOG.get("manifest.json");
      if (!object) return json({ error: "catalog manifest missing" }, 503);
      return new Response(request.method === "HEAD" ? null : object.body, {
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "public, max-age=300",
        },
      });
    }

    if (parts.length === 6 && parts[2] === "tiles") {
      const kind = parts[3];
      if (kind === "space" || kind === "shell" || kind === "sky") {
        return serveTile(env, kind, parts[4], parts[5]);
      }
    }

    if (parts.length === 5 && parts[2] === "core") {
      const [, , , level, filename] = parts;
      if (!/^L[0-3]$/.test(level) || !allowedCoreFiles.has(filename)) {
        return json({ error: "unknown core file" }, 404);
      }
      const object = await env.CATALOG.get(`${level}/${filename}`);
      if (!object) return json({ error: "unknown core file" }, 404);
      return binary(request.method === "HEAD" ? null : object.body, object.size, 86400);
    }
    return json({ error: "not found" }, 404);
  },
} satisfies ExportedHandler<Env>;
