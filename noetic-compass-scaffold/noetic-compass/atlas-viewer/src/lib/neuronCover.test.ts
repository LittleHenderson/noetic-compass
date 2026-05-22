import { describe, it, expect } from "vitest";
import {
  parseCoord,
  formatCoord,
  loadStage27FSnapshot,
  coordsForClass,
  type Stage27FData,
} from "./neuronCover";

describe("parseCoord / formatCoord round-trip", () => {
  const samples = [
    { s: "L5N2648", layer: 5, index: 2648 },
    { s: "L0N0", layer: 0, index: 0 },
    { s: "L11N3071", layer: 11, index: 3071 },
    { s: "L1N576", layer: 1, index: 576 },
    { s: "L5N84", layer: 5, index: 84 },
    { s: "L7N12345", layer: 7, index: 12345 },
  ];

  for (const { s, layer, index } of samples) {
    it(`parses ${s}`, () => {
      const c = parseCoord(s);
      expect(c.layer).toBe(layer);
      expect(c.index).toBe(index);
      expect(c.label).toBe(s);
    });

    it(`formats (${layer}, ${index}) -> ${s}`, () => {
      expect(formatCoord(layer, index)).toBe(s);
    });

    it(`round-trips ${s}`, () => {
      const c = parseCoord(s);
      expect(formatCoord(c.layer, c.index)).toBe(s);
    });
  }
});

describe("parseCoord error cases", () => {
  it("throws on lowercase prefix", () => {
    expect(() => parseCoord("l5n2648")).toThrow(/invalid coord/);
  });

  it("throws on missing N segment", () => {
    expect(() => parseCoord("L5")).toThrow(/invalid coord/);
  });

  it("throws on empty string", () => {
    expect(() => parseCoord("")).toThrow(/invalid coord/);
  });

  it("throws on swapped order", () => {
    expect(() => parseCoord("N5L2648")).toThrow(/invalid coord/);
  });

  it("throws on extra suffix", () => {
    expect(() => parseCoord("L5N2648x")).toThrow(/invalid coord/);
  });

  it("throws on negative index", () => {
    expect(() => parseCoord("L5N-2")).toThrow(/invalid coord/);
  });

  it("throws on non-string input", () => {
    expect(() => parseCoord(123 as unknown as string)).toThrow(/expected string/);
  });
});

describe("formatCoord error cases", () => {
  it("throws on negative layer", () => {
    expect(() => formatCoord(-1, 0)).toThrow(/layer/);
  });

  it("throws on non-integer index", () => {
    expect(() => formatCoord(0, 1.5)).toThrow(/index/);
  });
});

function makeValidSnapshot(): Record<string, unknown> {
  return {
    mlp_intermediate_dim: 3072,
    candidate_layers_per_class: {
      F1A: [1, 5],
      F1T: [1, 5],
      F1f: [5],
      F1E: [1, 5],
    },
    per_class_neuron_covers: {
      F1A: ["L5N2648", "L5N2948", "L5N325", "L5N2343"],
      F1T: ["L5N2346", "L5N230", "L5N1583", "L5N1127"],
      F1f: ["L5N84", "L5N1354", "L5N207", "L5N230"],
      F1E: ["L5N1580", "L5N529", "L5N2948", "L5N2648"],
    },
    row_reports: [
      {
        target: "F1T",
        candidate_layers: [1, 5],
        neuron_cover: ["L5N2346", "L5N230", "L5N1583", "L5N1127"],
        clean_margin: 7.615121465567857,
        targeted_drop: 2.4367720906769357,
      },
      {
        target: "F1A",
        candidate_layers: [1, 5],
        neuron_cover: ["L5N2648", "L5N2948", "L5N325", "L5N2343"],
        clean_margin: 7.0723537437091855,
        targeted_drop: 5.821502546710739,
      },
    ],
  };
}

describe("loadStage27FSnapshot", () => {
  it("loads a valid snapshot", () => {
    const snap = loadStage27FSnapshot(makeValidSnapshot());
    expect(snap.mlp_intermediate_dim).toBe(3072);
    expect(snap.per_class_neuron_covers.F1A).toHaveLength(4);
    expect(snap.row_reports).toHaveLength(2);
    expect(snap.row_reports[0].target).toBe("F1T");
    expect(snap.candidate_layers_per_class.F1f).toEqual([5]);
  });

  it("accepts row_reports nested under evaluation", () => {
    const raw = makeValidSnapshot();
    const rows = raw.row_reports;
    delete raw.row_reports;
    raw.evaluation = { row_reports: rows };
    const snap = loadStage27FSnapshot(raw);
    expect(snap.row_reports).toHaveLength(2);
  });

  it("throws on null input", () => {
    expect(() => loadStage27FSnapshot(null)).toThrow(/JSON object/);
  });

  it("throws on missing mlp_intermediate_dim", () => {
    const raw = makeValidSnapshot();
    delete raw.mlp_intermediate_dim;
    expect(() => loadStage27FSnapshot(raw)).toThrow(/mlp_intermediate_dim/);
  });

  it("throws on non-integer mlp_intermediate_dim", () => {
    const raw = makeValidSnapshot();
    raw.mlp_intermediate_dim = "3072";
    expect(() => loadStage27FSnapshot(raw)).toThrow(/mlp_intermediate_dim/);
  });

  it("throws on unknown class key in covers", () => {
    const raw = makeValidSnapshot();
    (raw.per_class_neuron_covers as Record<string, string[]>).F9X = ["L0N0"];
    expect(() => loadStage27FSnapshot(raw)).toThrow(/unknown class key "F9X"/);
  });

  it("throws on non-string entry in neuron cover", () => {
    const raw = makeValidSnapshot();
    (raw.per_class_neuron_covers as Record<string, unknown>).F1A = ["L5N1", 42];
    expect(() => loadStage27FSnapshot(raw)).toThrow(/per_class_neuron_covers\.F1A/);
  });

  it("throws on missing row_reports", () => {
    const raw = makeValidSnapshot();
    delete raw.row_reports;
    expect(() => loadStage27FSnapshot(raw)).toThrow(/row_reports/);
  });

  it("throws on row with invalid target", () => {
    const raw = makeValidSnapshot();
    (raw.row_reports as Array<Record<string, unknown>>)[0].target = "FXX";
    expect(() => loadStage27FSnapshot(raw)).toThrow(/target invalid/);
  });

  it("throws on row with non-numeric clean_margin", () => {
    const raw = makeValidSnapshot();
    (raw.row_reports as Array<Record<string, unknown>>)[0].clean_margin = "high";
    expect(() => loadStage27FSnapshot(raw)).toThrow(/clean_margin/);
  });
});

describe("coordsForClass", () => {
  let data: Stage27FData;

  it("returns parsed coords for a known class", () => {
    data = loadStage27FSnapshot(makeValidSnapshot());
    const coords = coordsForClass(data, "F1A");
    expect(coords).toHaveLength(4);
    expect(coords[0]).toEqual({ layer: 5, index: 2648, label: "L5N2648" });
    expect(coords[3]).toEqual({ layer: 5, index: 2343, label: "L5N2343" });
  });

  it("throws on class key absent from snapshot", () => {
    data = loadStage27FSnapshot(makeValidSnapshot());
    expect(() => coordsForClass(data, "F7E")).toThrow(/not present/);
  });
});
