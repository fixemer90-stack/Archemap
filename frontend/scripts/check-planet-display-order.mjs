import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import vm from "node:vm";
import ts from "typescript";

// Match the existing transpileModule behavior harness, including real TSX.
const require = createRequire(import.meta.url);
const root = resolve(dirname(new URL(import.meta.url).pathname), "../src");
const cache = new Map();
function load(path) {
  const filename = [path, `${path}.ts`, `${path}.tsx`].find(existsSync);
  assert.ok(filename, `Missing source module: ${path}`);
  if (cache.has(filename)) return cache.get(filename).exports;
  const sourceModule = { exports: {} };
  cache.set(filename, sourceModule);
  const compiled = ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
    fileName: filename,
  }).outputText;
  vm.runInThisContext(`(function(require, module, exports) {${compiled}\n})`, {
    filename,
  })(
    (id) =>
      id.startsWith("@/")
        ? load(resolve(root, id.slice(2)))
        : id.startsWith(".")
          ? load(resolve(dirname(filename), id))
          : require(id),
    sourceModule,
    sourceModule.exports,
  );
  return sourceModule.exports;
}

const { buildV2ReportReaderViewModel } = load(
  resolve(root, "lib/astrotype-v2/report-view-model"),
);
const { V2PlanetPositionsTable } = load(
  resolve(root, "components/astrotype-v2/report/V2PlanetPositionsTable"),
);
const main = [
  "Sun",
  "Moon",
  "Mercury",
  "Venus",
  "Mars",
  "Jupiter",
  "Saturn",
  "Uranus",
  "Neptune",
  "Pluto",
];
const russian = [
  "Солнце",
  "Луна",
  "Меркурий",
  "Венера",
  "Марс",
  "Юпитер",
  "Сатурн",
  "Уран",
  "Нептун",
  "Плутон",
];
const shuffled = [
  "Sun",
  "Moon",
  "Ascendant",
  "Jupiter",
  "Mars",
  "Mercury",
  "Neptune",
  "Pluto",
  "Saturn",
  "Uranus",
  "Venus",
];
const positions = shuffled.map((body, index) => ({
  body,
  sign: "Aries",
  house_number: index + 1,
  sign_degree: index + 0.125,
  degree_label: `${index}°07′`,
  retrograde: index % 2 === 0,
  sampled_aspects: [
    {
      body_a: body,
      body_b: "Moon",
      aspect_code: "trine",
      orb_degrees: index + 0.25,
    },
  ],
}));
const payload = {
  report: { id: "saved-report", status: "ready", version: 2 },
  infographic: { calculation_layer: { planet_positions: positions } },
};
const before = structuredClone(payload);
const rows =
  buildV2ReportReaderViewModel(payload).calculationLayer.planetPositions;
assert.deepEqual(
  rows.map((row) => row.body),
  [...russian, "Асцендент"],
  "saved DTO must become classically ordered localized VM rows",
);
function tableRows(element) {
  if (!element || typeof element !== "object") return [];
  if (Array.isArray(element)) return element.flatMap(tableRows);
  if (element.type === "tbody") return element.props.children;
  return tableRows(element.props?.children);
}
const rendered = tableRows(
  V2PlanetPositionsTable({ positions: [...rows].reverse() }),
);
assert.deepEqual(
  rendered.map((row) => row.props.children[0].props.children),
  [...russian, "Асцендент"],
  "actual table must order localized VM rows independently of input order",
);
for (const row of rows) {
  const index =
    row.body === "Асцендент"
      ? shuffled.indexOf("Ascendant")
      : shuffled.indexOf(main[russian.indexOf(row.body)]);
  assert.equal(row.houseNumber, positions[index].house_number);
  assert.equal(row.signDegree, positions[index].sign_degree);
  assert.equal(row.degreeLabel, positions[index].degree_label);
  assert.equal(row.retrograde, positions[index].retrograde);
  assert.equal(
    row.sampledAspects[0].orbDegrees,
    positions[index].sampled_aspects[0].orb_degrees,
  );
}
assert.deepEqual(
  payload,
  before,
  "building and rendering must not mutate the saved DTO",
);
console.log(
  "Planet display ordering: saved DTO -> localized VM -> actual table PASS",
);

// Exact persisted production order: MC used to jump ahead of every Russian row.
const persistedBodies = [
  "Sun",
  "Moon",
  "Ascendant",
  "Jupiter",
  "Lilith",
  "MC",
  "Mars",
  "Mercury",
  "Neptune",
  "North Node",
  "Pluto",
  "Saturn",
  "Uranus",
  "Venus",
];
const persistedPayload = {
  ...payload,
  infographic: {
    calculation_layer: {
      planet_positions: persistedBodies.map((body, index) => ({
        ...positions[0],
        body,
        sign_degree: index + 0.5,
        degree_label: `${index}°30′`,
      })),
    },
  },
};
const persistedBefore = structuredClone(persistedPayload);
const persistedRows =
  buildV2ReportReaderViewModel(persistedPayload).calculationLayer
    .planetPositions;
const expectedPersisted = [
  ...russian,
  "Северный узел",
  "Лилит",
  "Асцендент",
  "MC",
];
assert.deepEqual(
  persistedRows.map((row) => row.body),
  expectedPersisted,
);
assert.deepEqual(
  tableRows(V2PlanetPositionsTable({ positions: persistedRows })).map(
    (row) => row.props.children[0].props.children,
  ),
  expectedPersisted,
  "MC must not jump ahead of localized planets",
);
assert.equal(persistedRows.at(-1).signDegree, 5.5);
assert.deepEqual(persistedPayload, persistedBefore);
console.log(
  "Planet display ordering: exact persisted production DTO / localized MC regression PASS",
);

const { orderPlanetPositions } = load(
  resolve(root, "lib/astrology/planet-display-order"),
);
const extras = [
  "Chiron",
  "North Node",
  "South Node",
  "Lilith",
  "Part of Fortune",
  "Vertex",
  "Ascendant",
  "MC",
];
const extraRu = [
  "Хирон",
  "Северный узел",
  "Южный узел",
  "Лилит",
  "Парс Фортуны",
  "Вертекс",
  "Асцендент",
  "MC",
];
for (const names of [
  [...main, ...extras],
  [...russian, ...extraRu],
]) {
  const input = Object.freeze(
    [...names]
      .reverse()
      .map((body, index) =>
        Object.freeze({ body, index, nested: { numeric: index + 0.123 } }),
      ),
  );
  const output = orderPlanetPositions(input, (row) => row.body);
  assert.deepEqual(
    output.map((row) => row.body),
    names,
  );
  assert.notEqual(output, input);
  for (const row of output)
    assert.equal(
      row,
      input.find((original) => original.index === row.index),
    );
  assert.deepEqual(
    input.map((row) => row.body),
    [...names].reverse(),
  );
  const directRows = output.map((row) => ({ ...rows[0], body: row.body }));
  const directBefore = structuredClone(directRows);
  const directRendered = tableRows(
    V2PlanetPositionsTable({ positions: directRows }),
  );
  assert.equal(directRendered.length, names.length);
  assert.deepEqual(directRows, directBefore);
}
const aliases = [
  " asc ",
  "south_node",
  "NORTH-NODE",
  "Чёрная Луна",
  "Колесо Фортуны",
  "midheaven",
  "Раху",
  "Кету",
  "МС",
];
assert.deepEqual(
  orderPlanetPositions(aliases, (body) => body),
  [
    "NORTH-NODE",
    "Раху",
    "south_node",
    "Кету",
    "Чёрная Луна",
    "Колесо Фортуны",
    " asc ",
    "midheaven",
    "МС",
  ],
);
const duplicates = Object.freeze([
  Object.freeze({ body: "Zulu", id: 0 }),
  Object.freeze({ body: "Moon", id: 1 }),
  Object.freeze({ body: "Солнце", id: 2 }),
  Object.freeze({ body: "Alpha", id: 3 }),
  Object.freeze({ body: "Sun", id: 4 }),
  Object.freeze({ body: "", id: 5 }),
  Object.freeze({ body: "Moon", id: 6 }),
]);
assert.deepEqual(
  orderPlanetPositions(duplicates, (row) => row.body).map((row) => row.id),
  [2, 4, 1, 6, 0, 3, 5],
);
assert.deepEqual(
  orderPlanetPositions([], (row) => row.body),
  [],
);
console.log(
  "Planet display ordering: RU/EN main ten, extras, aliases, stable duplicates/unknowns, identity and nonmutation PASS",
);

const { toReportViewModel } = load(resolve(root, "lib/report/view-model"));
for (const nested of [false, true]) {
  const layer = {
    contract_version: "natal_infographic_data_v2",
    planet_positions: positions,
  };
  const data = {
    profile: {
      name: "Synthetic",
      birth_date: "1990-01-01",
      birth_time: "12:00",
      birth_time_accuracy: "exact",
      birth_place: "Test",
      timezone: "UTC",
    },
    chartSnapshot: { chart_data: {} },
    generatedReport: {
      report_data: nested
        ? { v2_infographic: { calculation_layer: layer } }
        : { calculation_layer: layer },
    },
  };
  const saved = structuredClone(data);
  const legacyRows =
    toReportViewModel(data).v2_calculation_layer.planet_positions;
  assert.deepEqual(
    legacyRows.map((row) => row.body),
    [...main, "Ascendant"],
    "legacy calculation VM must order both saved layer shapes",
  );
  for (const row of legacyRows)
    assert.equal(
      row,
      positions.find((original) => original.body === row.body),
    );
  assert.deepEqual(data, saved);
}
console.log(
  "Planet display ordering: legacy direct/nested calculation VM PASS",
);
