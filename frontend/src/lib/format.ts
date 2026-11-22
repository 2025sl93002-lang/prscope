export function relativeTime(epochSeconds: number | null | undefined): string {
  if (!epochSeconds) return "never";
  const diff = Date.now() / 1000 - epochSeconds;
  const abs = Math.abs(diff);
  const units: [number, string][] = [
    [60, "second"],
    [3600, "minute"],
    [86400, "hour"],
    [2592000, "day"],
    [31536000, "month"],
    [Infinity, "year"],
  ];
  let value = diff;
  let unit = "second";
  let prev = 1;
  for (const [limit, name] of units) {
    if (abs < limit) {
      value = diff / prev;
      unit = name;
      break;
    }
    prev = limit;
  }
  const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  return rtf.format(-Math.round(value), unit as Intl.RelativeTimeFormatUnit);
}

export function formatDate(epochSeconds: number | null | undefined): string {
  if (!epochSeconds) return "—";
  return new Date(epochSeconds * 1000).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function titleCase(s: string): string {
  return s.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
