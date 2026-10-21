// Mirrors the plan JSON written by toolkit/departments/storyboard.py (plus `audio` added at render time).

export type Scene = {
  id: string;
  kind: "hook" | "fact" | "check" | "cta";
  title: string;
  body: string;
  voice: string;
  duration_sec: number;
  visual: { kind: "data_card" | "stock" | "own"; src?: string };
};

export type Brand = {
  bg?: string;
  fg?: string;
  accent?: string;
  muted?: string;
  name?: string;
};

export type Plan = {
  id: string;
  project: string;
  rera_id: string;
  as_of: string;
  width: number;
  height: number;
  fps: number;
  duration_sec: number;
  disclaimer: string;
  brand: Brand;
  scenes: Scene[];
  audio?: string;
};
