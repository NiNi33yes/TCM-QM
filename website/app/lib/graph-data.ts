import herbsRaw from "../data/herbs.json";
import edgesRaw from "../data/edges.json";
import { getCompound, getGlobalPercentile } from "./data";

export type HerbEntity = (typeof herbsRaw)[number];
export type EvidenceEdge = (typeof edgesRaw)[number];
const herbs = herbsRaw as HerbEntity[];
const edges = edgesRaw as EvidenceEdge[];
const herbById = new Map(herbs.map(herb => [herb.id, herb]));
const edgesByHerb = new Map<string, EvidenceEdge[]>();
const edgesByCid = new Map<string, EvidenceEdge[]>();

for (const edge of edges) {
  edgesByHerb.set(edge.herbId, [...(edgesByHerb.get(edge.herbId) ?? []), edge]);
  edgesByCid.set(edge.cid, [...(edgesByCid.get(edge.cid) ?? []), edge]);
}

const aliases: Record<string, string> = { "丹參": "丹参", "黃芪": "黄芪", "當歸": "当归", "金銀花": "金银花" };
const normalize = (value: string) => (aliases[value.trim()] ?? value.trim()).toLocaleLowerCase();

export function findHerb(query: string) {
  const q = normalize(query);
  return herbs.find(herb => normalize(herb.name) === q || herb.id.toLocaleLowerCase() === q)
    ?? herbs.find(herb => normalize(herb.name).includes(q));
}

function herbRecords(herb: HerbEntity, sort: string) {
  const allEdges = edgesByHerb.get(herb.id) ?? [];
  const records = allEdges.flatMap(edge => {
    const compound = getCompound(edge.cid);
    return compound ? [{ edge, compound }] : [];
  }).sort((a, b) => {
    if (sort === "gap_asc") return a.compound.gapEv - b.compound.gapEv;
    if (sort === "gap_desc") return b.compound.gapEv - a.compound.gapEv;
    if (sort === "dipole_desc") return b.compound.dipoleDebye - a.compound.dipoleDebye;
    return Number(a.compound.cid) - Number(b.compound.cid);
  });
  return records.map(({ edge, compound }) => ({
    cid: compound.cid, title: compound.title, formula: compound.formula,
    gapEv: compound.gapEv, dipoleDebye: compound.dipoleDebye, qcStatus: compound.qcStatus,
    gapPercentile: getGlobalPercentile(compound.gapEv, "gapEv"),
    dipolePercentile: getGlobalPercentile(compound.dipoleDebye, "dipoleDebye"),
    sharedHerbCount: edgesByCid.get(compound.cid)?.length ?? 0,
    edge,
  }));
}

export function getHerbById(id: string) {
  return herbById.get(id);
}

export function getHerbSubgraph(query: string, sort: string, page: number, limit: number) {
  const herb = findHerb(query);
  if (!herb) return undefined;
  const items = herbRecords(herb, sort);
  return { herb, items: items.slice((page - 1) * limit, page * limit), total: items.length, page, limit };
}

export function getHerbCompounds(id: string, sort: string) {
  const herb = herbById.get(id) ?? findHerb(id);
  if (!herb) return undefined;
  const items = herbRecords(herb, sort);
  return { herb, items, total: items.length };
}

export function getCompoundHerbs(cid: string) {
  return (edgesByCid.get(cid) ?? []).map(edge => ({ edge, herb: herbById.get(edge.herbId) })).filter(item => item.herb);
}
