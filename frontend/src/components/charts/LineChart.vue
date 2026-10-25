<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

export interface Series {
  name: string;
  color: string;
  values: (number | null)[];
  line?: boolean;
  dots?: boolean;
  label?: boolean;
  step?: boolean;
}

export interface RefLine {
  y: number;
  label: string;
}

const props = withDefaults(
  defineProps<{
    series: Series[];
    xLabels: string[];
    height?: number;
    yFormat?: (v: number) => string;
    yMin?: number;
    yMax?: number;
    refs?: RefLine[];
  }>(),
  { height: 220, yFormat: (v: number) => v.toFixed(2), refs: () => [] },
);

const root = ref<HTMLElement | null>(null);
const width = ref(600);
const hover = ref<number | null>(null);
let ro: ResizeObserver | null = null;

onMounted(() => {
  if (!root.value) return;
  ro = new ResizeObserver(([e]) => (width.value = Math.max(240, e.contentRect.width)));
  ro.observe(root.value);
});
onBeforeUnmount(() => ro?.disconnect());

const pad = { l: 52, r: 92, t: 12, b: 26 };
const n = computed(() => props.xLabels.length);
const innerW = computed(() => width.value - pad.l - pad.r);
const innerH = computed(() => props.height - pad.t - pad.b);

const domain = computed(() => {
  const vals = props.series.flatMap((s) => s.values.filter((v): v is number => v !== null));
  vals.push(...props.refs.map((r) => r.y));
  let lo = props.yMin ?? Math.min(...vals);
  let hi = props.yMax ?? Math.max(...vals);
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [0, 1];
  if (lo === hi) {
    lo -= 1;
    hi += 1;
  }
  const span = hi - lo;
  return [props.yMin ?? lo - span * 0.08, props.yMax ?? hi + span * 0.08];
});

const x = (i: number) => pad.l + (n.value <= 1 ? innerW.value / 2 : (i / (n.value - 1)) * innerW.value);
const y = (v: number) => pad.t + innerH.value - ((v - domain.value[0]) / (domain.value[1] - domain.value[0])) * innerH.value;

const ticks = computed(() => {
  const [lo, hi] = domain.value;
  return Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);
});

const xTicks = computed(() => {
  const longest = Math.max(1, ...props.xLabels.map((l) => l.length));
  const step = Math.max(1, Math.ceil(n.value / Math.max(2, Math.floor(innerW.value / (longest * 6.5 + 24)))));
  return props.xLabels.map((l, i) => ({ l, i })).filter(({ i }) => i % step === 0);
});

function pathFor(s: Series) {
  let d = '';
  let pen = false;
  let prevY: number | null = null;
  s.values.forEach((v, i) => {
    if (v === null) return;
    if (!pen) {
      d += `M${x(i)},${y(v)}`;
      pen = true;
    } else if (s.step && prevY !== null) {
      d += `H${x(i)}V${y(v)}`;
    } else {
      d += `L${x(i)},${y(v)}`;
    }
    prevY = v;
  });
  return d;
}

function lastPoint(s: Series) {
  for (let i = s.values.length - 1; i >= 0; i--) if (s.values[i] !== null) return { i, v: s.values[i] as number };
  return null;
}

const directLabels = computed(() => {
  const out = props.series
    .filter((s) => s.label !== false && s.line !== false)
    .map((s) => ({ s, p: lastPoint(s) }))
    .filter((o) => o.p)
    .map((o) => ({ name: o.s.name, ref: false, x: pad.l + innerW.value + 8, y: y(o.p!.v) }));
  out.push(...props.refs.map((r) => ({ name: r.label, ref: true, x: pad.l + innerW.value + 8, y: y(r.y) })));
  out.sort((a, b) => a.y - b.y);
  for (let k = 1; k < out.length; k++) if (out[k].y - out[k - 1].y < 14) out[k].y = out[k - 1].y + 14;
  const overflow = out.length ? out[out.length - 1].y - (pad.t + innerH.value) : 0;
  if (overflow > 0) out.forEach((l) => (l.y -= overflow));
  return out;
});

function onMove(e: MouseEvent) {
  const rect = (e.currentTarget as SVGElement).getBoundingClientRect();
  const px = e.clientX - rect.left;
  if (n.value === 0) return;
  const i = n.value <= 1 ? 0 : Math.round(((px - pad.l) / innerW.value) * (n.value - 1));
  hover.value = Math.min(n.value - 1, Math.max(0, i));
}

const tip = computed(() => {
  if (hover.value === null) return null;
  const i = hover.value;
  const rows = props.series.map((s) => ({ name: s.name, color: s.color, v: s.values[i] })).filter((r) => r.v !== null && r.v !== undefined);
  if (!rows.length) return null;
  const top = Math.min(...rows.map((r) => y(r.v as number)));
  return { left: x(i), top, label: props.xLabels[i], rows };
});
</script>

<template>
  <div ref="root" class="chart">
    <svg :height="height" :viewBox="`0 0 ${width} ${height}`" @mousemove="onMove" @mouseleave="hover = null">
      <g class="grid">
        <line v-for="t in ticks" :key="t" :x1="pad.l" :x2="pad.l + innerW" :y1="y(t)" :y2="y(t)" />
      </g>
      <g class="axis">
        <text v-for="t in ticks" :key="'y' + t" :x="pad.l - 10" :y="y(t) + 3.5" text-anchor="end">{{ yFormat(t) }}</text>
        <text v-for="t in xTicks" :key="'x' + t.i" :x="x(t.i)" :y="height - 6" text-anchor="middle">{{ t.l }}</text>
      </g>
      <g v-for="r in refs" :key="r.label">
        <line :x1="pad.l" :x2="pad.l + innerW" :y1="y(r.y)" :y2="y(r.y)" stroke="#94a3b8" stroke-dasharray="4 4" stroke-width="1" />
      </g>
      <line v-if="tip" :x1="tip.left" :x2="tip.left" :y1="pad.t" :y2="pad.t + innerH" stroke="#cbd2dc" stroke-width="1" />
      <g v-for="s in series" :key="s.name">
        <path v-if="s.line !== false" :d="pathFor(s)" fill="none" :stroke="s.color" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
        <template v-if="s.dots">
          <template v-for="(v, i) in s.values" :key="i">
            <circle v-if="v !== null" :cx="x(i)" :cy="y(v)" :r="hover === i ? 5 : 4" :fill="s.color" stroke="#fff" stroke-width="2" />
          </template>
        </template>
      </g>
      <template v-if="hover !== null">
        <template v-for="s in series" :key="'h' + s.name">
          <circle v-if="!s.dots && s.values[hover] !== null && s.values[hover] !== undefined" :cx="x(hover)" :cy="y(s.values[hover] as number)" r="4.5" :fill="s.color" stroke="#fff" stroke-width="2" />
        </template>
      </template>
      <text v-for="l in directLabels" :key="'l' + l.name" class="label" :x="l.x" :y="l.y + 4" :style="l.ref ? 'fill: #8a94a6; font-weight: 500' : undefined">{{ l.name }}</text>
      <rect :x="pad.l" :y="pad.t" :width="innerW" :height="innerH" fill="transparent" />
    </svg>
    <div v-if="tip" class="tooltip" :style="{ left: tip.left + 20 + 'px', top: tip.top + 8 + 'px' }">
      <div class="muted">{{ tip.label }}</div>
      <div v-for="r in tip.rows" :key="r.name"><i :style="{ background: r.color }"></i>{{ r.name }} <b>{{ yFormat(r.v as number) }}</b></div>
    </div>
  </div>
</template>
