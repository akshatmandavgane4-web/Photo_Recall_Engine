/* Shared logic for the browser and the server function: filters, retrieval, exact counts. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Engine = factory();
})(this, function () {
  var STAGES = ["express", "understand", "evaluate", "refine"];
  var FILTER_WORDS = {
    failure_stage: { express: ["express"], understand: ["understand"], evaluate: ["evaluate", "recogni", "scan"], refine: ["refine", "refin"] },
    source: { reddit: ["reddit"], play_store: ["play store", "android"], app_store: ["app store", "ios", "iphone"] },
    photo_type: { document: ["document", "passport", "prescription"], screenshot: ["screenshot"], receipt: ["receipt", "bill"],
      person: ["person", "people photo"], place: ["place photo", "location"], object: ["object"], event: ["event", "trip"] },
    outcome: { abandoned: ["abandon", "gave up", "give up"], found: ["found", "succe"] }
  };
  var CUE_WORDS = { semantic_content: ["content", "what is in", "object"], episodic_context: ["occasion", "episod", "trip"],
    people: ["people", "person", "name", "face"], relative_time: ["time", "date", "year", "when"],
    approx_place: ["place", "location", "where"], visual_attributes: ["visual", "colour", "color", "looked"],
    text_in_image: ["text"], source_purpose: ["whatsapp", "source", "purpose", "sent"] };
  var STOP = ("the a an of to in on for and or is are was were do does did what which who how why when where with about " +
    "by from that this it they them their users user people photos photo google me show tell give any some " +
    "most many much more than compare vs between at be can could").split(" ");

  function prepare(rows) {
    return rows.map(function (r) {
      var cues = [], quotes = [];
      (r.remembered_cues || []).forEach(function (c) { if (cues.indexOf(c.cue) < 0) cues.push(c.cue); quotes.push(c.quote); });
      var o = {}; for (var k in r) o[k] = r[k];
      o.cues = cues.sort(); o.cue_quotes = quotes.join("; ");
      return o;
    });
  }
  function findFilters(q) {
    var ql = q.toLowerCase(), f = {};
    Object.keys(FILTER_WORDS).forEach(function (col) {
      var hit = Object.keys(FILTER_WORDS[col]).filter(function (v) {
        return FILTER_WORDS[col][v].some(function (w) { return ql.indexOf(w) >= 0; });
      });
      if (hit.length) f[col] = hit;
    });
    return f;
  }
  function applyFilters(data, f) {      // a filter that would empty the set is skipped (same as the display scope)
    var sub = data;
    Object.keys(f).forEach(function (col) {
      var n = sub.filter(function (r) { return f[col].indexOf(r[col]) >= 0; });
      if (n.length) sub = n;
    });
    return sub;
  }
  function retrieve(data, q, k) {
    k = k || 14;
    var f = findFilters(q), sub = data, empty = false;
    Object.keys(f).forEach(function (col) {
      var n = sub.filter(function (r) { return f[col].indexOf(r[col]) >= 0; });
      if (n.length) sub = n; else empty = true;
    });
    if (empty) return { filters: f, evidence: [] };
    var ql = q.toLowerCase();
    var words = (ql.match(/[a-z]{3,}/g) || []).filter(function (w, i, a) { return STOP.indexOf(w) < 0 && a.indexOf(w) === i; });
    var want = Object.keys(CUE_WORDS).filter(function (c) { return CUE_WORDS[c].some(function (w) { return ql.indexOf(w) >= 0; }); });
    var scored = sub.map(function (r, i) {
      var text = [r.failure_detail, r.verbatim, r.cue_quotes, r.retrieval_purpose, r.workaround || ""].join(" ").toLowerCase();
      var s = words.filter(function (w) { return text.indexOf(w) >= 0; }).length * 2 +
        want.filter(function (c) { return r.cues.indexOf(c) >= 0; }).length * 2 + (r.cues.length ? 1 : 0) + r.severity / 10;
      return { r: r, s: s, i: i };
    }).sort(function (a, b) { return b.s - a.s || a.i - b.i; }).slice(0, k);
    return { filters: f, evidence: scored.map(function (x, n) {
      var r = x.r;
      return { n: n + 1, id: r.incident_id, stage: r.failure_stage, source: r.source, photo_type: r.photo_type, outcome: r.outcome,
        remembered: r.cue_quotes, detail: r.failure_detail, quote: r.verbatim, url: r.url };
    }) };
  }
  function tally(rows, key) {
    var m = {};
    rows.forEach(function (r) { var vs = key(r); (Array.isArray(vs) ? vs : [vs]).forEach(function (v) { m[v] = (m[v] || 0) + 1; }); });
    return Object.keys(m).map(function (k) { return [k, m[k]]; }).sort(function (a, b) { return b[1] - a[1]; });
  }
  function stageCounts(rows) {
    var m = {}; rows.forEach(function (r) { m[r.failure_stage] = (m[r.failure_stage] || 0) + 1; });
    return STAGES.map(function (s) { return [s, m[s] || 0]; }).concat([["unknown", (m.unknown || 0) + (m.none || 0)]]);
  }
  function exactStats(rows, label) {
    if (!rows.length) return label + ": 0 incidents.";
    var c = function (key) { return tally(rows, function (r) { return r[key]; }).map(function (x) { return x[0] + " " + x[1]; }).join(", "); };
    var cues = tally(rows, function (r) { return r.cues; });
    return label + ": " + rows.length + " incidents. By failure stage: " + c("failure_stage") + ". By source: " + c("source") +
      ". By photo type: " + c("photo_type") + ". By outcome: " + c("outcome") + ". By search strategy: " + c("query_strategy") +
      ". Incidents stating what was remembered: " + rows.filter(function (r) { return r.cues.length; }).length +
      "; cue types mentioned: " + (cues.map(function (x) { return x[0] + " " + x[1]; }).join(", ") || "none") + ".";
  }
  function statsBlock(data, f) {
    var sources = tally(data, function (r) { return r.source; }).map(function (x) { return x[0]; }).sort();
    var block = exactStats(data, "Whole dataset") + "\n" +
      sources.map(function (s) { return exactStats(data.filter(function (r) { return r.source === s; }), "Source " + s); }).join("\n");
    var keys = Object.keys(f);
    if (keys.length) block += "\n" + exactStats(applyFilters(data, f), "Matching your filters (" +
      keys.map(function (k) { return k + "=" + f[k].join("/"); }).join("; ") + ")");
    return block;
  }
  function fallback(data, q) {          // used when the language model cannot be reached
    var r = retrieve(data, q);
    if (!r.evidence.length) return { answer: "No evidence found for this in the dataset. Try asking about a failure stage, a source, or what people remembered.", cited: [], ev: [], llm: false };
    var keys = Object.keys(r.filters), sub = applyFilters(data, r.filters);
    return { answer: "The language model is unavailable right now, so here are the exact counts and the closest matching incidents instead.\n\n" +
      exactStats(sub, keys.length ? "Matching your question" : "Whole dataset"),
      cited: r.evidence.slice(0, 6).map(function (x) { return x.n; }), ev: r.evidence, llm: false };
  }
  return { STAGES: STAGES, prepare: prepare, findFilters: findFilters, applyFilters: applyFilters, retrieve: retrieve,
    stageCounts: stageCounts, tally: tally, exactStats: exactStats, statsBlock: statsBlock, fallback: fallback };
});
