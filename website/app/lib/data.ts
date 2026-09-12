import raw from "../data/compounds.json";

export type Compound = typeof raw[number];
const compounds = raw as Compound[];
const byCid = new Map(compounds.map(item => [item.cid, item]));

export function getCompound(cid: string) { return byCid.get(cid); }
export function getCompounds() { return compounds; }
export function getAdjacentCompounds(cid: string) {
  const index = compounds.findIndex(item => item.cid === cid);
  return {
    previous: index > 0 ? compounds[index - 1] : undefined,
    next: index >= 0 && index < compounds.length - 1 ? compounds[index + 1] : undefined,
  };
}
export type CompoundQuery = {
  scope?: "all" | "compound" | "herb";
  qc?: string;
  herb?: "all" | "mapped" | "unmapped";
  gapMin?: number;
  gapMax?: number;
  massMin?: number;
  massMax?: number;
  sort?: "cid" | "gap_asc" | "gap_desc" | "mass_asc" | "mass_desc" | "dipole_desc";
};

export function searchCompounds(query: string, options: CompoundQuery = {}) {
  const q = query.trim().toLocaleLowerCase();
  const scope = options.scope ?? "all";
  const result = compounds.filter(item => {
    const compoundMatch = !q || item.cid === q || item.title.toLocaleLowerCase().includes(q) ||
      item.formula.toLocaleLowerCase().includes(q) || item.inchiKey.toLocaleLowerCase().includes(q);
    const herbMatch = !q || item.herbNames.toLocaleLowerCase().includes(q);
    const textMatch = scope === "compound" ? compoundMatch : scope === "herb" ? herbMatch : compoundMatch || herbMatch;
    if (!textMatch) return false;
    if (options.qc && options.qc !== "all" && item.qcStatus !== options.qc) return false;
    if (options.herb === "mapped" && item.herbCount === 0) return false;
    if (options.herb === "unmapped" && item.herbCount > 0) return false;
    if (options.gapMin != null && item.gapEv < options.gapMin) return false;
    if (options.gapMax != null && item.gapEv > options.gapMax) return false;
    if (options.massMin != null && item.molecularWeight < options.massMin) return false;
    if (options.massMax != null && item.molecularWeight > options.massMax) return false;
    return true;
  });
  const numericCid = (value: string) => Number(value) || Number.MAX_SAFE_INTEGER;
  return result.sort((a, b) => {
    switch (options.sort) {
      case "gap_asc": return a.gapEv - b.gapEv;
      case "gap_desc": return b.gapEv - a.gapEv;
      case "mass_asc": return a.molecularWeight - b.molecularWeight;
      case "mass_desc": return b.molecularWeight - a.molecularWeight;
      case "dipole_desc": return b.dipoleDebye - a.dipoleDebye;
      default: return numericCid(a.cid) - numericCid(b.cid);
    }
  });
}

const percentileFields = ["gapEv", "dipoleDebye"] as const;
const sortedDistributions = Object.fromEntries(
  percentileFields.map(field => [field, compounds.map(item => item[field]).filter(Number.isFinite).sort((a, b) => a - b)]),
) as Record<(typeof percentileFields)[number], number[]>;

export function getGlobalPercentile(value: number, field: (typeof percentileFields)[number]) {
  const values = sortedDistributions[field];
  let low = 0, high = values.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (values[middle] <= value) low = middle + 1;
    else high = middle;
  }
  return Math.round((low / values.length) * 100);
}
