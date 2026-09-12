import { NextRequest, NextResponse } from "next/server";
import { getCompoundHerbs, getHerbCompounds, getHerbSubgraph } from "../../lib/graph-data";
import { getCompound, getGlobalPercentile } from "../../lib/data";

export async function GET(request: NextRequest) {
  const cid = (request.nextUrl.searchParams.get("cid") || "").replace(/\D/g, "");
  if (cid) {
    const connections = getCompoundHerbs(cid);
    const compound = getCompound(cid);
    const item = compound ? {
      cid: compound.cid, title: compound.title, formula: compound.formula,
      gapEv: compound.gapEv, dipoleDebye: compound.dipoleDebye, qcStatus: compound.qcStatus,
      gapPercentile: getGlobalPercentile(compound.gapEv, "gapEv"),
      dipolePercentile: getGlobalPercentile(compound.dipoleDebye, "dipoleDebye"),
      sharedHerbCount: connections.length,
      edge: connections[0]?.edge ?? null,
    } : null;
    return NextResponse.json({ cid, compound: item, connections }, { headers: { "Cache-Control": "public, max-age=300" } });
  }
  const herbId = (request.nextUrl.searchParams.get("herb") || "").trim();
  if (herbId) {
    const sort = request.nextUrl.searchParams.get("sort") || "cid";
    const result = getHerbCompounds(herbId, sort);
    if (!result) return NextResponse.json({ error: "未找到该药材实体。" }, { status: 404 });
    return NextResponse.json(result, { headers: { "Cache-Control": "public, max-age=300", "X-Robots-Tag": "noindex" } });
  }
  const q = (request.nextUrl.searchParams.get("q") || "丹参").slice(0, 40);
  const sort = request.nextUrl.searchParams.get("sort") || "cid";
  const page = Math.max(1, Number(request.nextUrl.searchParams.get("page")) || 1);
  const limit = Math.min(40, Math.max(5, Number(request.nextUrl.searchParams.get("limit")) || 20));
  const result = getHerbSubgraph(q, sort, page, limit);
  if (!result) return NextResponse.json({ error: "未找到该药材实体。请尝试规范名或常用繁体名。" }, { status: 404 });
  return NextResponse.json(result, { headers: { "Cache-Control": "public, max-age=120", "X-Robots-Tag": "noindex" } });
}
