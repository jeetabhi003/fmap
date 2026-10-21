import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type { Brand, Plan, Scene } from "./types";

const DEFAULT_BRAND: Required<Brand> = {
  bg: "#10201a",
  fg: "#f4f1ea",
  accent: "#7fc4a8",
  muted: "#a9b7ae",
  name: "Find Me A Property",
};

const LABELS: Record<Scene["kind"], string> = {
  hook: "WHAT WE CHECKED",
  fact: "VERIFIED",
  check: "STILL TO CHECK",
  cta: "FREE",
};

// Instagram covers roughly the top 220px and bottom 420px of a 1920px reel with its UI.
const SAFE_TOP = 260;
const SAFE_BOTTOM = 460;

const SceneCard: React.FC<{ scene: Scene; index: number; total: number; brand: Required<Brand> }> = ({
  scene,
  index,
  total,
  brand,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rise = spring({ frame, fps, config: { damping: 200 } });
  const bodyIn = interpolate(frame, [8, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const isId = /^P[0-9A-Z]{10,15}/.test(scene.body);

  return (
    <AbsoluteFill style={{ padding: `${SAFE_TOP}px 90px ${SAFE_BOTTOM}px`, justifyContent: "center" }}>
      <div style={{ color: brand.accent, fontSize: 34, letterSpacing: 6, fontWeight: 700 }}>
        {LABELS[scene.kind]} · {index + 1}/{total}
      </div>
      <div
        style={{
          color: brand.fg,
          fontSize: scene.title.length > 28 ? 76 : 92,
          fontWeight: 800,
          lineHeight: 1.08,
          marginTop: 28,
          transform: `translateY(${(1 - rise) * 60}px)`,
          opacity: rise,
        }}
      >
        {scene.title}
      </div>
      <div style={{ width: 160 * rise, height: 8, background: brand.accent, borderRadius: 4, marginTop: 36 }} />
      <div
        style={{
          color: brand.muted,
          fontSize: isId ? 64 : scene.body.length > 60 ? 44 : 54,
          fontFamily: isId ? "ui-monospace, Menlo, monospace" : undefined,
          letterSpacing: isId ? 2 : 0,
          lineHeight: 1.3,
          marginTop: 36,
          opacity: bodyIn,
        }}
      >
        {scene.body}
      </div>
    </AbsoluteFill>
  );
};

export const Reel: React.FC<Plan> = (plan) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const brand = { ...DEFAULT_BRAND, ...plan.brand };
  let from = 0;

  return (
    <AbsoluteFill style={{ background: brand.bg, fontFamily: "Inter, Helvetica, Arial, sans-serif" }}>
      {plan.audio ? <Audio src={staticFile(plan.audio)} /> : null}
      <div style={{ position: "absolute", top: SAFE_TOP - 70, left: 90, right: 90, height: 8, background: "#ffffff22", borderRadius: 4 }}>
        <div style={{ width: `${(frame / durationInFrames) * 100}%`, height: "100%", background: brand.accent, borderRadius: 4 }} />
      </div>
      {plan.scenes.map((scene, i) => {
        const frames = Math.round(scene.duration_sec * fps);
        const seq = (
          <Sequence key={scene.id} from={from} durationInFrames={frames}>
            <SceneCard scene={scene} index={i} total={plan.scenes.length} brand={brand} />
          </Sequence>
        );
        from += frames;
        return seq;
      })}
      <div
        style={{
          position: "absolute",
          bottom: SAFE_BOTTOM - 120,
          left: 90,
          right: 90,
          color: brand.muted,
          fontSize: 28,
          lineHeight: 1.35,
        }}
      >
        {brand.name} · MahaRERA {plan.rera_id} · facts as of {plan.as_of}
        <br />
        {plan.disclaimer}
      </div>
    </AbsoluteFill>
  );
};
