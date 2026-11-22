import { useState } from "react";
import { PackageCheck } from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, EmptyState, Skeleton } from "../components/ui";
import { NoScan } from "../components/Layout";
import { UpdateBadge } from "../lib/badges";
import { PackageDrawer } from "../components/PackageDrawer";

const PRIORITY = { major: 0, minor: 1, patch: 2, prerelease: 3 } as Record<string, number>;

export function Updates() {
  const { currentScanId } = useApp();
  const [pkg, setPkg] = useState<string | null>(null);
  const { data, loading } = useAsync(
    () => (currentScanId ? api.packages(currentScanId, {}) : Promise.resolve(null)),
    [currentScanId],
  );
  if (!currentScanId) return <NoScan />;
  if (loading) return <Skeleton h={400} />;
  if (!data) return null;

  const outdated = data.packages
    .filter((p) => ["major", "minor", "patch", "prerelease"].includes(p.update_type ?? ""))
    .sort((a, b) => (PRIORITY[a.update_type!] ?? 9) - (PRIORITY[b.update_type!] ?? 9));

  const unknown = data.packages.filter((p) => p.update_type === "unknown").length;

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Updates</h2>
          <p>{outdated.length} packages have newer releases · {unknown} could not be verified</p>
        </div>
      </div>
      {outdated.length === 0 ? (
        <EmptyState icon={<PackageCheck />} title="Everything is up to date">
          No newer releases were found for the installed versions{unknown ? ` (${unknown} unverified).` : "."}
        </EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Package</th><th>Installed</th><th>Latest</th><th>Update</th><th>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {outdated.map((p) => (
                <tr key={p.node_id} className="clickable" onClick={() => setPkg(p.name)}>
                  <td className="mono" style={{ fontWeight: 540 }}>{p.name}</td>
                  <td className="mono muted">{p.version}</td>
                  <td className="mono">{p.latest ?? "—"}</td>
                  <td><UpdateBadge type={p.update_type} /></td>
                  <td className="dim" style={{ fontSize: "var(--text-sm)" }}>
                    {p.data?.update?.recommendation ?? ""}
                    {p.is_direct && <Badge tone="accent">direct</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {pkg && <PackageDrawer scanId={currentScanId} name={pkg} onClose={() => setPkg(null)} />}
    </>
  );
}
