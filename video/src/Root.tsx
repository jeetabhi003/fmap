import { Composition } from "remotion";
import { Reel } from "./Reel";
import type { Plan } from "./types";

const sample: Plan = {
  id: "sample",
  project: "Sample Project",
  rera_id: "P51900000000",
  as_of: "2026-10-09",
  width: 1080,
  height: 1920,
  fps: 30,
  duration_sec: 8,
  disclaimer: "Research, not advice. Verify on MahaRERA before you pay.",
  brand: {},
  scenes: [
    { id: "s1", kind: "hook", title: "₹9 to 31 Cr in Worli", body: "What can you actually verify?", voice: "", duration_sec: 4, visual: { kind: "data_card" } },
    { id: "s2", kind: "cta", title: "Free buyer's checklist", body: "Link in bio", voice: "", duration_sec: 4, visual: { kind: "data_card" } },
  ],
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel}
    defaultProps={sample}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={240}
    calculateMetadata={({ props }) => ({
      width: props.width,
      height: props.height,
      fps: props.fps,
      durationInFrames: Math.round(props.scenes.reduce((t, s) => t + s.duration_sec, 0) * props.fps),
    })}
  />
);
