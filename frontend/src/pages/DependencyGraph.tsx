import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { type Core } from "cytoscape";
import fcose from "cytoscape-fcose";
import {
  Crosshair,
  List,
  Maximize2,
  Minus,
  Plus,
  Search,
} from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, Button, Card, CardHead, EmptyState, Skeleton } from "../components/ui";
import { NoScan } from "../components/Layout";
import { PackageDrawer } from "../components/PackageDrawer";
import type { GraphNode } from "../api/types";

cytoscape.use(fcose);

function nodeColor(n: GraphNode): string {
  if (n.root) return "#7c6cf0";
  if (n.vuln_count && n.vuln_count > 0)
    return n.max_severity === "critical" || n.max_severity === "high" ? "#dc5a4b" : "#d9922b";
  if (n.update_type === "major" || n.license_verdict === "restricted") return "#d9922b";
  return "#5b9d6b";
}

// Heat scale for blast-radius mode: green (isolated) → red (many dependents).
function blastColor(ratio: number): string {
  if (ratio >= 0.66) return "#dc5a4b";
  if (ratio >= 0.33) return "#d9922b";
  if (ratio > 0) return "#c9b24a";
  return "#5b9d6b";
}

type ColorMode = "health" | "blast";

export function DependencyGraph() {
  const { currentScanId } = useApp();
  const [includeDev, setIncludeDev] = useState(true);
  const [includeOpt, setIncludeOpt] = useState(true);
  const [directOnly, setDirectOnly] = useState(false);
  const [colorMode, setColorMode] = useState<ColorMode>("health");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [showList, setShowList] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const { data, loading } = useAsync(
    () => (currentScanId ? api.graph(currentScanId, includeDev, includeOpt) : Promise.resolve(null)),
    [currentScanId, includeDev, includeOpt],
  );

  const maxBlast = useMemo(
    () => Math.max(1, ...(data?.nodes ?? []).map((n) => n.blast_radius ?? 0)),
    [data],
  );

  const elements = useMemo(() => {
    if (!data) return [];
    let nodes = data.nodes;
    let edges = data.edges;
    if (directOnly) {
      const keep = new Set(nodes.filter((n) => n.direct || n.root).map((n) => n.id));
      nodes = nodes.filter((n) => keep.has(n.id));
      edges = edges.filter((e) => keep.has(e.source) && keep.has(e.target));
    }
    return [
      ...nodes.map((n) => {
        const ratio = (n.blast_radius ?? 0) / maxBlast;
        return {
          data: {
            id: n.id,
            label: n.root ? "project" : n.name,
            name: n.name,
            color: n.root ? "#7c6cf0" : colorMode === "blast" ? blastColor(ratio) : nodeColor(n),
            size: n.root
              ? 46
              : colorMode === "blast"
                ? 18 + Math.round(ratio * 34)
                : 20 + Math.min(18, (n.dependents ?? 0) * 2),
            direct: n.direct || n.root,
            root: n.root,
          },
        };
      }),
      ...edges.map((e) => ({ data: { id: `${e.source}->${e.target}`, source: e.source, target: e.target } })),
    ];
  }, [data, directOnly, colorMode, maxBlast]);

  useEffect(() => {
    if (!containerRef.current || elements.length === 0) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: elements as any,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            width: "data(size)",
            height: "data(size)",
            label: "data(label)",
            "font-size": 9,
            "font-family": "var(--font-mono)",
            color: "var(--text-2)",
            "text-margin-y": 5,
            "text-valign": "bottom",
            "border-width": 2,
            "border-color": "var(--surface-0)",
            "min-zoomed-font-size": 8,
          },
        },
        { selector: 'node[?direct]', style: { "border-color": "var(--accent)", "border-width": 2.5 } },
        { selector: 'node[?root]', style: { shape: "round-rectangle", "font-size": 11, color: "var(--text-1)" } },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "var(--border-strong)",
            "target-arrow-color": "var(--border-strong)",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.7,
            "curve-style": "bezier",
            opacity: 0.5,
          },
        },
        { selector: "node.faded", style: { opacity: 0.12 } },
        { selector: "edge.faded", style: { opacity: 0.04 } },
        { selector: "node.hi", style: { "border-color": "var(--accent)", "border-width": 4 } },
        { selector: "edge.hi", style: { "line-color": "var(--accent)", "target-arrow-color": "var(--accent)", opacity: 1, width: 2 } },
      ],
      layout: { name: "fcose", animate: false, quality: "default", nodeRepulsion: 6000, idealEdgeLength: 70 } as any,
      wheelSensitivity: 0.2,
    });
    cyRef.current = cy;

    cy.on("tap", "node", (evt) => {
      const d = evt.target.data();
      if (d.root) return;
      setSelected(d.name);
    });
    cy.on("mouseover", "node", (evt) => highlightNeighborhood(cy, evt.target));
    cy.on("mouseout", "node", () => clearHighlight(cy));

    return () => cy.destroy();
  }, [elements]);

  function highlightNeighborhood(cy: Core, node: any) {
    const hood = node.closedNeighborhood();
    cy.elements().addClass("faded");
    hood.removeClass("faded").addClass("hi");
  }
  function clearHighlight(cy: Core) {
    cy.elements().removeClass("faded hi");
  }

  function doSearch(term: string) {
    setQ(term);
    const cy = cyRef.current;
    if (!cy || !term) {
      cy?.elements().removeClass("faded hi");
      return;
    }
    const matches = cy.nodes().filter((n) => n.data("name")?.toLowerCase().includes(term.toLowerCase()));
    cy.elements().addClass("faded");
    matches.removeClass("faded").addClass("hi");
    if (matches.length) cy.animate({ fit: { eles: matches, padding: 80 } }, { duration: 300 });
  }

  const zoom = (factor: number) => {
    const cy = cyRef.current;
    if (cy) cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  };

  if (!currentScanId) return <NoScan />;

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Dependency Graph</h2>
          <p>{data ? `${data.nodes.length - 1} packages, ${data.edges.length} relationships` : "Loading…"}</p>
        </div>
        <Button variant="secondary" onClick={() => setShowList((v) => !v)}>
          <List size={16} /> {showList ? "Hide" : "Text"} list
        </Button>
      </div>

      <Card>
        <div className="row wrap spread" style={{ padding: "var(--sp-3) var(--sp-4)", borderBottom: "1px solid var(--border)", gap: "var(--sp-3)" }}>
          <div className="field-wrap" style={{ flex: "1 1 220px", maxWidth: 300 }}>
            <Search size={16} />
            <input className="input input-search" placeholder="Search & focus a package…" value={q} onChange={(e) => doSearch(e.target.value)} />
          </div>
          <div className="row wrap" style={{ gap: 6 }}>
            <FilterChip active={!directOnly} onClick={() => setDirectOnly(false)}>Full tree</FilterChip>
            <FilterChip active={directOnly} onClick={() => setDirectOnly(true)}>Direct only</FilterChip>
            <FilterChip active={includeDev} onClick={() => setIncludeDev((v) => !v)}>Dev deps</FilterChip>
            <FilterChip active={includeOpt} onClick={() => setIncludeOpt((v) => !v)}>Optional</FilterChip>
            <span style={{ width: 1, alignSelf: "stretch", background: "var(--border)", margin: "0 2px" }} />
            <FilterChip active={colorMode === "health"} onClick={() => setColorMode("health")}>Color: health</FilterChip>
            <FilterChip active={colorMode === "blast"} onClick={() => setColorMode("blast")}>Color: blast radius</FilterChip>
            <Button icon variant="ghost" onClick={() => zoom(1.25)} aria-label="Zoom in"><Plus size={16} /></Button>
            <Button icon variant="ghost" onClick={() => zoom(0.8)} aria-label="Zoom out"><Minus size={16} /></Button>
            <Button icon variant="ghost" onClick={() => cyRef.current?.animate({ fit: { eles: cyRef.current.elements(), padding: 40 } }, { duration: 300 })} aria-label="Fit"><Maximize2 size={16} /></Button>
          </div>
        </div>

        {loading && <div className="card-pad"><Skeleton h={480} /></div>}
        <div style={{ position: "relative" }}>
          <div ref={containerRef} style={{ height: "60vh", minHeight: 440, width: "100%" }} aria-label="Dependency graph canvas" role="img" />
          <div style={{ position: "absolute", left: 14, bottom: 14, background: "color-mix(in srgb, var(--surface-0) 88%, transparent)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", padding: "8px 12px", fontSize: "var(--text-xs)", backdropFilter: "blur(6px)" }}>
            {colorMode === "health" ? (
              <>
                <div className="row" style={{ gap: 14 }}>
                  <span className="row" style={{ gap: 5 }}><span className="sev-dot" style={{ background: "#dc5a4b" }} /> Vulnerable</span>
                  <span className="row" style={{ gap: 5 }}><span className="sev-dot" style={{ background: "#d9922b" }} /> Outdated / license</span>
                  <span className="row" style={{ gap: 5 }}><span className="sev-dot" style={{ background: "#5b9d6b" }} /> Healthy</span>
                </div>
                <div className="muted" style={{ marginTop: 4 }}>Blue outline = direct · node size = dependents · hover to focus</div>
              </>
            ) : (
              <>
                <div className="row" style={{ gap: 14 }}>
                  <span className="row" style={{ gap: 5 }}><span className="sev-dot" style={{ background: "#dc5a4b" }} /> High blast radius</span>
                  <span className="row" style={{ gap: 5 }}><span className="sev-dot" style={{ background: "#d9922b" }} /> Medium</span>
                  <span className="row" style={{ gap: 5 }}><span className="sev-dot" style={{ background: "#5b9d6b" }} /> Isolated</span>
                </div>
                <div className="muted" style={{ marginTop: 4 }}>Size & color = how many packages would be affected if this one were compromised</div>
              </>
            )}
          </div>
        </div>
      </Card>

      {data && (
        <Card>
          <CardHead
            title="Single points of failure"
            subtitle="Packages the most of your project transitively depends on — the highest-impact supply-chain targets"
          />
          <div className="card-pad">
            <div className="row wrap" style={{ gap: 8 }}>
              {[...data.nodes]
                .filter((n) => !n.root && (n.blast_radius ?? 0) > 0)
                .sort((a, b) => (b.blast_radius ?? 0) - (a.blast_radius ?? 0))
                .slice(0, 10)
                .map((n) => {
                  const ratio = (n.blast_radius ?? 0) / maxBlast;
                  return (
                    <button
                      key={n.id}
                      className="card"
                      style={{ padding: "8px 12px", boxShadow: "none", cursor: "pointer", background: "var(--surface-2)", textAlign: "left" }}
                      onClick={() => setSelected(n.name)}
                    >
                      <div className="row" style={{ gap: 8 }}>
                        <span className="sev-dot" style={{ background: blastColor(ratio) }} />
                        <span className="mono" style={{ fontWeight: 540 }}>{n.name}</span>
                        {(n.vuln_count ?? 0) > 0 && <Badge tone="danger">vulnerable</Badge>}
                      </div>
                      <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 2 }}>
                        {n.blast_radius} package{(n.blast_radius ?? 0) === 1 ? "" : "s"} depend on it
                      </div>
                    </button>
                  );
                })}
              {data.nodes.filter((n) => !n.root && (n.blast_radius ?? 0) > 0).length === 0 && (
                <span className="muted">No shared dependencies — every package has a single dependent.</span>
              )}
            </div>
          </div>
        </Card>
      )}

      {showList && data && (
        <Card className="card-pad">
          <strong>Textual dependency list (accessibility)</strong>
          <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>
            {data.nodes.filter((n) => !n.root).sort((a, b) => a.name.localeCompare(b.name)).map((n) => (
              <button key={n.id} className="badge badge-neutral" style={{ cursor: "pointer" }} onClick={() => setSelected(n.name)}>
                <span className="sev-dot" style={{ background: nodeColor(n) }} /> {n.name} {n.direct && <Badge tone="accent">direct</Badge>}
              </button>
            ))}
          </div>
        </Card>
      )}

      {data && data.nodes.length <= 1 && !loading && (
        <EmptyState icon={<Crosshair />} title="No graph to display">This scan has no resolved dependencies (was a lockfile present?).</EmptyState>
      )}

      {selected && <PackageDrawer scanId={currentScanId} name={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

function FilterChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      className="tab"
      style={{ borderBottom: "none", borderRadius: "var(--radius-full)", padding: "5px 12px", background: active ? "var(--accent-soft)" : "var(--surface-2)", color: active ? "var(--accent-text)" : "var(--text-2)" }}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
