// A second source file that uses `node-fetch` via a dynamic import and uses a
// scoped helper. This exercises DepLens's ability to find usage beyond the
// entry point, including ESM-style dynamic imports inside CommonJS.

async function fetchStatus(url) {
  const { default: fetch } = await import("node-fetch");
  const res = await fetch(url);
  return res.status;
}

module.exports = { fetchStatus };
