// Demo entry point for the DepLens fixture project.
// It genuinely imports several of the declared dependencies so that DepLens's
// usage analysis has real evidence to find. Note that `moment` is intentionally
// declared in package.json but never imported here — DepLens should surface it
// as a "potentially unused" candidate (with appropriate uncertainty).

const express = require("express");
const _ = require("lodash");
const chalk = require("chalk");
const minimist = require("minimist");

const args = minimist(process.argv.slice(2));
const app = express();

app.get("/health", (req, res) => {
  res.json({ status: "ok", uptime: _.round(process.uptime(), 2) });
});

const port = _.defaultTo(args.port, 3000);
app.listen(port, () => {
  console.log(chalk.green(`demo app listening on ${port}`));
});

module.exports = app;
