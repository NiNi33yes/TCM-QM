"use client";

import type { Core, ElementDefinition } from "cytoscape";
import { FormEvent, Fragment, useEffect, useRef, useState } from "react";

type EdgeEvidence = {
  id: string;
  confidence: string;
  method: string;
  sourceDatabase: string;
  sourceLocator: string;
  sourceSnapshot: string;
  evidenceCount: string;
};
type Item = {
  cid: string;
  title: string;
  formula: string;
  gapEv: number;
  dipoleDebye: number;
  qcStatus: string;
  gapPercentile: number;
  dipolePercentile: number;
  sharedHerbCount: number;
  edge: EdgeEvidence | null;
};
type Herb = { id: string; name: string; edgeCount: number };
type Lens = "cid" | "gap_asc" | "gap_desc" | "dipole_desc";
type Step = { kind: "herb" | "compound"; id: string; label: string };
type HerbFocus = { kind: "herb"; herb: Herb; compounds: Item[] };
type CompoundFocus = {
  kind: "compound";
  item: Item;
  sharedHerbs: { herb: Herb; edge: EdgeEvidence }[];
};
type Focus = HerbFocus | CompoundFocus;

const lensLabels: Record<Lens, string> = {
  cid: "按 CID 浏览",
  gap_asc: "低能隙优先",
  gap_desc: "高能隙优先",
  dipole_desc: "高偶极矩优先",
};
const methodLabels: Record<string, string> = {
  direct_pubchem_cid_and_herb_relation_from_TCMSP_molecule_page:
    "TCMSP 分子页直接 CID–药材关系",
  pubchem_title_exact_global_unique: "标题精确匹配 · 全局唯一",
  "pubchem_title_exact+herb_context": "标题精确匹配 · 药材语境确认",
  pubchem_title_exact_ambiguous: "标题精确匹配 · 存在歧义",
};

const stepKey = (step: Step) => `${step.kind}:${step.id}`;
const SHARED_CAP = 18;

function edgeIdBetween(a: Step, b: Step): string | null {
  if (a.kind === "herb" && b.kind === "compound") return `edge-${a.id}-${b.id}`;
  if (a.kind === "compound" && b.kind === "herb")
    return `shared-${b.id}-${a.id}`;
  return null;
}

function applyPathEdges(instance: Core, path: Step[]) {
  instance.edges().removeClass("path");
  for (let i = 0; i < path.length - 1; i++) {
    const id = edgeIdBetween(path[i], path[i + 1]);
    if (id) instance.$id(id).addClass("path");
  }
}

function applyFocusHighlight(instance: Core, focusId: string) {
  instance.elements().removeClass("dimmed focused");
  const focusNode = instance.$id(focusId);
  if (!focusNode.length) return;
  focusNode.addClass("focused");
  const hood = focusNode.closedNeighborhood();
  const incident = focusNode.connectedEdges();
  instance.nodes().difference(hood).addClass("dimmed");
  instance.edges().difference(incident).addClass("dimmed");
}

function layoutRadially(instance: Core, centerId: string, newIds: string[]) {
  const center = instance.$id(centerId);
  if (!center.length) return;
  const pos = center.position();
  const neighbors = center.connectedNodes();
  const existing = neighbors.filter(
    (node) => !newIds.includes(node.id()),
  ).length;
  const total = existing + newIds.length;
  const radius = Math.max(150, Math.min(620, total * 12));
  newIds.forEach((id, index) => {
    const angle = ((existing + index) / Math.max(1, total)) * Math.PI * 2;
    instance
      .$id(id)
      .position({
        x: pos.x + Math.cos(angle) * radius,
        y: pos.y + Math.sin(angle) * radius,
      });
  });
}

export function GraphExplorer({ initialCid }: { initialCid?: string }) {
  const container = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const exploredNodes = useRef(new Set<string>());
  const exploredEdges = useRef(new Set<string>());
  const itemByCid = useRef(new Map<string, Item>());
  const focusCache = useRef(new Map<string, Focus>());
  const expandHerbRef = useRef<(query: string) => Promise<void>>(
    async () => {},
  );
  const expandCompoundRef = useRef<(cid: string) => Promise<void>>(
    async () => {},
  );

  const [input, setInput] = useState("丹参");
  const [lens, setLens] = useState<Lens>("cid");
  const [path, setPath] = useState<Step[]>([]);
  const [focus, setFocus] = useState<Focus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [stats, setStats] = useState({ nodes: 0, edges: 0 });

  function pushStep(step: Step) {
    setPath((prev) => {
      const index = prev.findIndex(
        (item) => item.kind === step.kind && item.id === step.id,
      );
      const base = index >= 0 ? prev.slice(0, index) : prev;
      return [...base, step];
    });
  }

  async function expandHerb(query: string) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        `/api/graph?herb=${encodeURIComponent(query)}&sort=${lens}`,
      );
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "关系数据加载失败");
      const herb = result.herb as Herb;
      const items = result.items as Item[];
      const instance = cyRef.current;
      if (instance) {
        const isRoot = exploredNodes.current.size === 0;
        const herbNodeId = `herb-${herb.id}`;
        const additions: ElementDefinition[] = [];
        const newCompoundIds: string[] = [];
        if (!exploredNodes.current.has(herbNodeId)) {
          additions.push({
            data: {
              id: herbNodeId,
              label: herb.name,
              type: "herb",
              herbId: herb.id,
              degree: herb.edgeCount,
            },
            position: isRoot ? { x: 0, y: 0 } : undefined,
          });
          exploredNodes.current.add(herbNodeId);
        }
        for (const item of items) {
          itemByCid.current.set(item.cid, item);
          const nodeId = `cid-${item.cid}`;
          if (!exploredNodes.current.has(nodeId)) {
            additions.push({
              data: {
                id: nodeId,
                label: item.formula,
                subtitle: `CID ${item.cid}`,
                type: "compound",
                cid: item.cid,
                gap: item.gapEv,
                degree: item.sharedHerbCount,
              },
            });
            exploredNodes.current.add(nodeId);
            newCompoundIds.push(nodeId);
          }
          const edgeId = `edge-${herb.id}-${item.cid}`;
          if (!exploredEdges.current.has(edgeId)) {
            additions.push({
              data: {
                id: edgeId,
                source: herbNodeId,
                target: nodeId,
                type: "evidence",
                confidence: item.edge.confidence,
              },
            });
            exploredEdges.current.add(edgeId);
          }
        }
        if (additions.length) instance.add(additions);
        if (isRoot)
          instance
            .layout({
              name: "cose",
              animate: false,
              fit: true,
              padding: 36,
              nodeRepulsion: 60000,
              idealEdgeLength: 110,
            })
            .run();
        else if (newCompoundIds.length)
          layoutRadially(instance, herbNodeId, newCompoundIds);
        applyFocusHighlight(instance, herbNodeId);
      }
      const step: Step = { kind: "herb", id: herb.id, label: herb.name };
      const nextFocus: Focus = { kind: "herb", herb, compounds: items };
      focusCache.current.set(stepKey(step), nextFocus);
      pushStep(step);
      setFocus(nextFocus);
      setStats({
        nodes: exploredNodes.current.size,
        edges: exploredEdges.current.size,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "关系数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  function mergeSharedHerbs(
    cid: string,
    item: Item,
    connections: { herb: Herb; edge: EdgeEvidence }[],
    center: { x: number; y: number },
  ) {
    const instance = cyRef.current;
    if (!instance) return;
    const nodeId = `cid-${cid}`;
    const additions: ElementDefinition[] = [];
    if (!exploredNodes.current.has(nodeId)) {
      additions.push({
        data: {
          id: nodeId,
          label: item.formula,
          subtitle: `CID ${item.cid}`,
          type: "compound",
          cid: item.cid,
          gap: item.gapEv,
          degree: item.sharedHerbCount,
        },
        position: center,
      });
      exploredNodes.current.add(nodeId);
    }
    const visible = connections.slice(0, SHARED_CAP);
    visible.forEach((relation, index) => {
      const herbId = `herb-${relation.herb.id}`;
      if (!exploredNodes.current.has(herbId)) {
        const angle = (index / Math.max(1, visible.length)) * Math.PI * 2;
        additions.push({
          data: {
            id: herbId,
            label: relation.herb.name,
            type: "herb",
            herbId: relation.herb.id,
            degree: relation.herb.edgeCount,
          },
          position: {
            x: center.x + Math.cos(angle) * 135,
            y: center.y + Math.sin(angle) * 135,
          },
        });
        exploredNodes.current.add(herbId);
      }
      const edgeId = `shared-${relation.herb.id}-${cid}`;
      if (!exploredEdges.current.has(edgeId)) {
        additions.push({
          data: {
            id: edgeId,
            source: nodeId,
            target: herbId,
            type: "shared",
            confidence: relation.edge.confidence,
          },
        });
        exploredEdges.current.add(edgeId);
      }
    });
    if (additions.length) instance.add(additions);
    applyFocusHighlight(instance, nodeId);
  }

  async function expandCompound(cid: string) {
    const item = itemByCid.current.get(cid);
    if (!item) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/graph?cid=${cid}`);
      const result = await response.json();
      const connections = (result.connections || []) as {
        herb: Herb;
        edge: EdgeEvidence;
      }[];
      if (cyRef.current)
        mergeSharedHerbs(
          cid,
          item,
          connections,
          cyRef.current.$id(`cid-${cid}`).position(),
        );
      const step: Step = { kind: "compound", id: cid, label: item.formula };
      const nextFocus: Focus = {
        kind: "compound",
        item,
        sharedHerbs: connections,
      };
      focusCache.current.set(stepKey(step), nextFocus);
      pushStep(step);
      setFocus(nextFocus);
      setStats({
        nodes: exploredNodes.current.size,
        edges: exploredEdges.current.size,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "关系数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function expandCompoundFromCid(cid: string) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/graph?cid=${cid}`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "关系数据加载失败");
      const item = result.compound as Item | null;
      if (!item) throw new Error("未找到该成分的图谱记录");
      const connections = (result.connections || []) as {
        herb: Herb;
        edge: EdgeEvidence;
      }[];
      itemByCid.current.set(cid, item);
      if (cyRef.current) {
        mergeSharedHerbs(cid, item, connections, { x: 0, y: 0 });
        cyRef.current.fit(undefined, 40);
      }
      const step: Step = { kind: "compound", id: cid, label: item.formula };
      const nextFocus: Focus = {
        kind: "compound",
        item,
        sharedHerbs: connections,
      };
      focusCache.current.set(stepKey(step), nextFocus);
      pushStep(step);
      setFocus(nextFocus);
      setStats({
        nodes: exploredNodes.current.size,
        edges: exploredEdges.current.size,
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "关系数据加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    expandHerbRef.current = expandHerb;
    expandCompoundRef.current = expandCompound;
  });

  useEffect(() => {
    if (!container.current) return;
    let active = true;
    let instance: Core | null = null;

    import("cytoscape").then(({ default: cytoscape }) => {
      if (!active || !container.current) return;
      instance = cytoscape({
      container: container.current,
      elements: [],
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-family": "Microsoft YaHei",
            "font-size": 12,
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": 96,
            "border-width": 2,
            "border-color": "#ffffff",
            "overlay-opacity": 0,
            "transition-property": "opacity",
            "transition-duration": 180,
          },
        },
        {
          selector: 'node[type="herb"]',
          style: {
            shape: "ellipse",
            width: "mapData(degree,1,100,50,92)",
            height: "mapData(degree,1,100,50,92)",
            "background-color": "#17483b",
            color: "#ffffff",
            "font-size": 13,
            "font-weight": 700,
          },
        },
        {
          selector: 'node[type="compound"]',
          style: {
            shape: "round-rectangle",
            width: 74,
            height: 46,
            "background-color": "mapData(gap,0,8,#c1543f,#eee9dc)",
            color: "#17211d",
            "border-color": "#b49b78",
          },
        },
        {
          selector: "node.focused",
          style: {
            "border-width": 4,
            "border-color": "#b44937",
            "underlay-color": "#b44937",
            "underlay-opacity": 0.14,
            "underlay-padding": 9,
          },
        },
        { selector: "node.dimmed", style: { opacity: 0.28 } },
        {
          selector: "edge",
          style: {
            width: 1.3,
            "line-color": "#9db4aa",
            "curve-style": "bezier",
            opacity: 0.72,
          },
        },
        {
          selector: 'edge[type="shared"]',
          style: {
            "line-color": "#c58a61",
            "line-style": "dashed",
            width: 1.8,
          },
        },
        { selector: "edge.dimmed", style: { opacity: 0.12 } },
        {
          selector: "node.hovered",
          style: {
            "underlay-color": "#b44937",
            "underlay-opacity": 0.2,
            "underlay-padding": 8,
            opacity: 1,
          },
        },
        {
          selector: "edge.path",
          style: {
            "line-color": "#b44937",
            width: 2.6,
            "line-style": "solid",
            opacity: 1,
          },
        },
      ],
      layout: { name: "preset" },
      minZoom: 0.3,
      maxZoom: 2.5,
      wheelSensitivity: 0.22,
    });
      instance.on("tap", "node", (event) => {
      const data = event.target.data();
      if (data.type === "herb") expandHerbRef.current(data.herbId);
      else if (data.type === "compound") expandCompoundRef.current(data.cid);
    });
      instance.on("mouseover", "node", (event) => {
      event.target.addClass("hovered");
      if (container.current) container.current.style.cursor = "pointer";
    });
      instance.on("mouseout", "node", (event) => {
      event.target.removeClass("hovered");
      if (container.current) container.current.style.cursor = "default";
    });
      cyRef.current = instance;
      if (initialCid) expandCompoundFromCid(initialCid);
      else expandHerbRef.current("丹参");
    }).catch(() => {
      if (active) setError("知识图谱组件加载失败");
    });

    return () => {
      active = false;
      instance?.destroy();
      cyRef.current = null;
    };
  }, [initialCid]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (cyRef.current) applyPathEdges(cyRef.current, path);
  }, [path]);

  function backTo(index: number) {
    const step = path[index];
    if (!step) return;
    setPath((prev) => prev.slice(0, index + 1));
    setFocus(focusCache.current.get(stepKey(step)) ?? null);
    const instance = cyRef.current;
    if (instance)
      applyFocusHighlight(
        instance,
        step.kind === "herb" ? `herb-${step.id}` : `cid-${step.id}`,
      );
  }

  function reset() {
    cyRef.current?.elements().remove();
    exploredNodes.current.clear();
    exploredEdges.current.clear();
    itemByCid.current.clear();
    focusCache.current.clear();
    setPath([]);
    setFocus(null);
    setError("");
    setLoading(false);
    setStats({ nodes: 0, edges: 0 });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!input.trim()) return;
    reset();
    expandHerb(input.trim());
  }

  async function changeLens(next: Lens) {
    setLens(next);
    if (focus?.kind === "herb") {
      try {
        const response = await fetch(
          `/api/graph?herb=${encodeURIComponent(focus.herb.id)}&sort=${next}`,
        );
        const result = await response.json();
        if (response.ok) {
          const updated: Focus = {
            kind: "herb",
            herb: result.herb,
            compounds: result.items,
          };
          focusCache.current.set(
            stepKey({
              kind: "herb",
              id: result.herb.id,
              label: result.herb.name,
            }),
            updated,
          );
          setFocus(updated);
        }
      } catch {
        /* 保留当前焦点即可 */
      }
    }
  }

  function exportFocus() {
    if (!focus) return;
    const quote = (value: unknown) =>
      `"${String(value ?? "").replaceAll('"', '""')}"`;
    if (focus.kind === "herb") {
      const header = [
        "herb_id",
        "herb_name",
        "cid",
        "formula",
        "title",
        "gap_ev",
        "dipole_debye",
        "global_gap_percentile",
        "global_dipole_percentile",
        "shared_herb_count",
        "match_confidence",
        "match_method",
        "source_locator",
        "source_snapshot",
      ];
      const rows = focus.compounds.map((item) => [
        focus.herb.id,
        focus.herb.name,
        item.cid,
        item.formula,
        item.title,
        item.gapEv,
        item.dipoleDebye,
        item.gapPercentile,
        item.dipolePercentile,
        item.sharedHerbCount,
        item.edge?.confidence ?? "",
        item.edge?.method ?? "",
        item.edge?.sourceLocator ?? "",
        item.edge?.sourceSnapshot ?? "",
      ]);
      downloadCsv(
        `${focus.herb.name}_compounds.csv`,
        [header, ...rows].map((row) => row.map(quote).join(",")).join("\r\n"),
      );
    } else {
      const header = [
        "cid",
        "formula",
        "shared_herb_id",
        "shared_herb_name",
        "match_confidence",
        "match_method",
        "source_locator",
        "source_snapshot",
      ];
      const rows = focus.sharedHerbs.map(({ herb, edge }) => [
        focus.item.cid,
        focus.item.formula,
        herb.id,
        herb.name,
        edge.confidence,
        edge.method,
        edge.sourceLocator,
        edge.sourceSnapshot,
      ]);
      downloadCsv(
        `cid_${focus.item.cid}_shared_herbs.csv`,
        [header, ...rows].map((row) => row.map(quote).join(",")).join("\r\n"),
      );
    }
  }

  function downloadCsv(filename: string, content: string) {
    const blob = new Blob(["﻿" + content], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="graph-explorer">
      <form className="graph-search" onSubmit={submit}>
        <div>
          <small>BUILD AN EVIDENCE SUBGRAPH</small>
          <h2>输入一味药材，沿证据边自由探索成分与量子性质</h2>
        </div>
        <div>
          <label className="sr-only" htmlFor="herb-query">
            药材名称
          </label>
          <input
            id="herb-query"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="例如：丹参、柴胡、金银花"
          />
          <button type="submit">开始探索 →</button>
        </div>
      </form>
      <div className="graph-boundary">
        <b>证据边界</b>
        <span>
          16,918 条经裁决的 TCMSP 唯一边均为分子页直接关系，覆盖 495
          味药材与全部 3,196 个 CID；382
          条旧版独有关系全部排除并保留在审计账本；不推断含量、药效、靶点或临床因果。
        </span>
      </div>
      <div className="graph-workspace">
        <aside className="graph-controls">
          <small>DISCOVERY LENS</small>
          <h3>展开排序</h3>
          {(Object.keys(lensLabels) as Lens[]).map((key) => (
            <button
              type="button"
              className={lens === key ? "active" : ""}
              onClick={() => changeLens(key)}
              key={key}
            >
              <span className="control-dot" aria-hidden="true" />
              {lensLabels[key]}
            </button>
          ))}
          <dl>
            <div>
              <dt>已探索节点</dt>
              <dd>{stats.nodes}</dd>
            </div>
            <div>
              <dt>已探索边</dt>
              <dd>{stats.edges}</dd>
            </div>
            <div>
              <dt>路径步数</dt>
              <dd>{path.length}</dd>
            </div>
          </dl>
          <p className="graph-control-hint">
            点击画布中任意药材或成分节点，即可沿证据边继续向任意方向探索；点击上方路径可逐级回退。
          </p>
        </aside>
        <div className="graph-canvas">
          <header>
            <div className="graph-breadcrumb">
              <span>EVIDENCE PATH</span>
              <nav>
                {path.map((step, index) => (
                  <Fragment key={stepKey(step)}>
                    {index > 0 && <i className="crumb-arrow">→</i>}
                    <button
                      type="button"
                      className={index === path.length - 1 ? "current" : ""}
                      onClick={() => backTo(index)}
                    >
                      {step.kind === "herb"
                        ? step.label
                        : step.label || `CID ${step.id}`}
                    </button>
                  </Fragment>
                ))}
              </nav>
            </div>
            <span className="graph-tools">
              <button type="button" onClick={exportFocus}>
                导出焦点 CSV
              </button>
              <button
                type="button"
                onClick={() => cyRef.current?.fit(undefined, 30)}
              >
                适配画布
              </button>
              <button type="button" onClick={reset}>
                清空探索
              </button>
              {loading && <i className="spinner" aria-label="加载中" />}
            </span>
          </header>
          <div className="stage-wrap">
            <div
              ref={container}
              className="cytoscape-stage"
              aria-label="药材成分关系网络"
            />
            {loading && path.length === 0 && (
              <div className="loading-state overlay" aria-live="polite">
                <span className="spinner" />
                <b>正在构建关系视图</b>
              </div>
            )}
            {error && path.length === 0 && (
              <div className="empty-state overlay">
                <b>{error}</b>
                <span>请检查名称后重试。</span>
              </div>
            )}
          </div>
          <div className="graph-legend">
            <span>
              <i className="legend-herb" />
              药材
            </span>
            <span>
              <i className="legend-compound" />
              成分（低能隙偏暖）
            </span>
            <span>
              <i className="legend-shared" />
              共享关系
            </span>
            <small>拖动节点 · 滚轮缩放 · 点击任意节点继续展开</small>
          </div>
          <div className="graph-mobile-list">
            {focus?.kind === "herb" &&
              focus.compounds.map((item) => (
                <button key={item.cid} onClick={() => expandCompound(item.cid)}>
                  <b>{item.formula}</b>
                  <span>CID {item.cid}</span>
                  <em>{item.gapEv.toFixed(2)} eV</em>
                </button>
              ))}
            {focus?.kind === "compound" &&
              focus.sharedHerbs.slice(0, SHARED_CAP).map(({ herb }) => (
                <button key={herb.id} onClick={() => expandHerb(herb.id)}>
                  <b>{herb.name}</b>
                  <span>{herb.edgeCount} 个关联成分</span>
                  <em>→</em>
                </button>
              ))}
          </div>
        </div>
        <aside className="graph-insight">
          <small>NODE & EDGE INSIGHT</small>
          <h3>节点与来源证据</h3>
          {!focus ? (
            <p>点击画布中的节点，从任意方向展开并查看节点级详情。</p>
          ) : focus.kind === "herb" ? (
            <>
              <div className="focus-identity">
                <b>{focus.herb.name}</b>
                <span>
                  药材实体 · {focus.compounds.length} 个关联成分
                  <small>全部关联 {focus.herb.edgeCount} 条证据边</small>
                </span>
              </div>
              <div className="focus-metrics">
                <div>
                  <span>关联成分</span>
                  <b>{focus.herb.edgeCount}</b>
                  <small>按当前排序逐条展开</small>
                </div>
              </div>
              <div className="edge-evidence">
                <span>继续探索</span>
                <p>
                  点击画布中的任一成分节点，展开它与其它药材的共享关系；再点击任一药材节点，展开它自己的成分。共享关系为虚线边。
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="focus-identity">
                <b>{focus.item.formula}</b>
                <span>
                  {focus.item.title || `CID ${focus.item.cid}`}
                  <small>PubChem CID {focus.item.cid}</small>
                </span>
              </div>
              <div className="focus-metrics">
                <div>
                  <span>HOMO–LUMO 能隙</span>
                  <b>{focus.item.gapEv.toFixed(3)} eV</b>
                  <small>全库第 {focus.item.gapPercentile} 百分位</small>
                </div>
                <div>
                  <span>偶极矩</span>
                  <b>{focus.item.dipoleDebye.toFixed(3)} D</b>
                  <small>全库第 {focus.item.dipolePercentile} 百分位</small>
                </div>
                <div>
                  <span>共享药材</span>
                  <b>{focus.item.sharedHerbCount}</b>
                  <small>
                    图中已展开 {Math.min(focus.sharedHerbs.length, SHARED_CAP)}{" "}
                    味
                  </small>
                  {focus.sharedHerbs.length > SHARED_CAP && (
                    <em className="graph-omitted">
                      另有 {focus.sharedHerbs.length - SHARED_CAP} 味未显示
                    </em>
                  )}
                </div>
              </div>
              {focus.item.edge && (
                <div className="edge-evidence">
                  <span>匹配置信类</span>
                  <b>{focus.item.edge.confidence}</b>
                  <span>匹配方法</span>
                  <p>
                    {methodLabels[focus.item.edge.method] ||
                      focus.item.edge.method}
                  </p>
                  <span>来源定位</span>
                  <code>{focus.item.edge.sourceLocator}</code>
                  <small>
                    快照 {focus.item.edge.sourceSnapshot} ·{" "}
                    {focus.item.edge.evidenceCount} 条证据记录
                  </small>
                </div>
              )}
              <p>全库百分位基于 3,196 条冻结记录计算，仅用于描述相对位置。</p>
              <a href={`/compound/${focus.item.cid}`}>打开完整分子记录 →</a>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
