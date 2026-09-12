import { NextRequest, NextResponse } from "next/server";
import { searchCompounds } from "../../lib/data";

const windows = new Map<string, { count: number; reset: number }>();

export async function GET(request: NextRequest) {
  const ip = request.headers.get("cf-connecting-ip") || request.headers.get("x-forwarded-for") || "local";
  const now = Date.now(); const current = windows.get(ip);
  if (!current || current.reset < now) windows.set(ip, { count: 1, reset: now + 60_000 });
  else if (++current.count > 90) return NextResponse.json({ error: "请求过于频繁，请稍后再试。" }, { status: 429, headers: { "Retry-After": "60" } });

  const q = (request.nextUrl.searchParams.get("q") || "").slice(0, 80);
  const value = (name: string) => {
    const raw = request.nextUrl.searchParams.get(name);
    if (raw == null || raw === "") return undefined;
    const parsed = Number(raw); return Number.isFinite(parsed) ? parsed : undefined;
  };
  const page = Math.max(1, Number(request.nextUrl.searchParams.get("page")) || 1);
  const limit = Math.min(20, Math.max(1, Number(request.nextUrl.searchParams.get("limit")) || 12));
  const found = searchCompounds(q, {
    scope: (request.nextUrl.searchParams.get("scope") || "all") as "all" | "compound" | "herb",
    qc: request.nextUrl.searchParams.get("qc") || "all",
    herb: (request.nextUrl.searchParams.get("herb") || "all") as "all" | "mapped" | "unmapped",
    gapMin: value("gapMin"), gapMax: value("gapMax"), massMin: value("massMin"), massMax: value("massMax"),
    sort: (request.nextUrl.searchParams.get("sort") || "cid") as "cid" | "gap_asc" | "gap_desc" | "mass_asc" | "mass_desc" | "dipole_desc",
  });
  const items = found.slice((page - 1) * limit, page * limit).map((compound) => ({
    cid: compound.cid,
    title: compound.title,
    formula: compound.formula,
    molecularWeight: compound.molecularWeight,
    homoEv: compound.homoEv,
    lumoEv: compound.lumoEv,
    gapEv: compound.gapEv,
    dipoleDebye: compound.dipoleDebye,
    qcStatus: compound.qcStatus,
    herbCount: compound.herbCount,
  }));
  return NextResponse.json({ items, total: found.length, page, limit }, { headers: { "Cache-Control": "public, max-age=60", "X-Robots-Tag": "noindex" } });
}
