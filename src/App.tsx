import {
  Activity,
  Boxes,
  ChevronDown,
  Cpu,
  Database,
  Layers3,
  Radar,
  Route,
  Snowflake,
  SplitSquareVertical,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type TensorInfo = {
  name?: string;
  file: string;
  shard_number: number | null;
  dtype: string;
  shape: number[];
  data_offsets: [number, number];
  bytes: number;
  human_bytes: string;
  matches_shape_bytes: boolean;
};

type SliceInfo = {
  relative_offsets: [number, number];
  bytes: number;
  human_bytes: string;
};

type ExpertRecord = {
  id: string;
  layer: number;
  expert: number;
  layer_type: string;
  is_full_attention: boolean;
  files: string[];
  shards: number[];
  is_split_across_shards: boolean;
  total_bytes: number;
  human_total_bytes: string;
  down_proj: { file: string; shape: number[]; slice: SliceInfo | null } | null;
  gate_up_proj: { file: string; shape: number[]; slice: SliceInfo | null } | null;
  routing: null;
};

type LayerRecord = {
  layer: number;
  layer_label: string;
  layer_type: string;
  is_full_attention: boolean;
  bytes: number;
  human_bytes: string;
  expert_group_bytes: number;
  expert_group_human_bytes: string;
  per_expert_bytes: number;
  per_expert_human_bytes: string;
  router_bytes: number;
  router_human_bytes: string;
  shared_mlp_bytes: number;
  shared_mlp_human_bytes: string;
  expert_files: string[];
  expert_shards: number[];
  is_expert_split_across_shards: boolean;
  tensors: Record<string, TensorInfo>;
};

type ShardRecord = {
  file: string;
  shard_number: number | null;
  file_size: number;
  human_file_size: string;
  tensor_count: number;
  tensor_bytes: number;
  human_tensor_bytes: string;
  text_bytes: number;
  human_text_bytes: string;
  vision_bytes: number;
  human_vision_bytes: string;
};

type TensorPattern = {
  pattern: string;
  count: number;
};

type Manifest = {
  schema_version: number;
  generated_at: string;
  model_dir: string;
  model: {
    architecture: string;
    dtype: string;
    num_hidden_layers: number;
    num_experts: number;
    top_k_experts: number;
    hidden_size: number;
    moe_intermediate_size: number;
    intermediate_size: number;
    max_position_embeddings: number;
    sliding_window: number;
    vocab_size: number;
    total_parameters: number;
    total_size: number;
    human_total_size: string;
    layer_type_counts: Record<string, number>;
  };
  summary: {
    tensor_count: number;
    shard_count: number;
    expert_record_count: number;
    human_total_layer_bytes: string;
    human_total_expert_group_bytes: string;
    human_total_router_bytes: string;
    human_total_shared_mlp_bytes: string;
    expert_layers_split_across_shards: number[];
    expert_layer_split_count: number;
    human_per_expert_bytes: string;
  };
  shards: ShardRecord[];
  layers: LayerRecord[];
  experts: ExpertRecord[];
  tensor_patterns: TensorPattern[];
  routing_trace: { status: string; description: string };
};

type RoutingExpert = {
  id: string;
  layer: number;
  expert: number;
  count: number;
  share: number;
  rank: number;
};

type RoutingLayer = {
  layer: number;
  layer_label: string;
  layer_type: string;
  source_tensor: string;
  total_selections: number;
  nonzero_experts: number;
  zero_experts: number;
  max_count: number;
  min_nonzero_count: number;
  mean_count: number;
  counts: number[];
};

type RoutingTrace = {
  schema_version: number;
  label?: string;
  status: "ready";
  source: {
    kind: string;
    imatrix_path: string;
    datasets: string[];
    chunk_count: number;
    chunk_size: number;
  };
  summary: {
    total_selections: number;
    max_count: number;
    zero_expert_slots: number;
    nonzero_expert_slots: number;
    layers_with_counts: number;
  };
  layers: RoutingLayer[];
  experts: RoutingExpert[];
  hot_experts: RoutingExpert[];
  cold_experts: RoutingExpert[];
};

type RoutingComparisonExpert = {
  id: string;
  layer: number;
  expert: number;
  on_count: number;
  off_count: number;
  delta_count: number;
  on_share: number;
  off_share: number;
  delta_share: number;
};

type ReasoningComparison = {
  top_reasoning_on: RoutingComparisonExpert[];
  top_reasoning_off: RoutingComparisonExpert[];
  experts?: RoutingComparisonExpert[];
};

type ThemeMode = "reasoning_off" | "reasoning_on";

type ThemeBundle = {
  schema_version: number;
  summary: {
    theme_count: number;
    trace_count: number;
    themes: string[];
  };
  themes: Record<string, { label: string; modes: ThemeMode[] }>;
  traces: Record<string, Partial<Record<ThemeMode, RoutingTrace>>>;
  comparisons: Record<string, ReasoningComparison>;
};

type RoutingTimelineExpert = {
  id: string;
  layer: number;
  expert: number;
  chunk_counts: number[];
  total_count: number;
  early_count: number;
  later_count: number;
  active_chunks: number;
  first_active_chunk: number | null;
  last_active_chunk: number | null;
  early_share: number;
  status: "early_only" | "late_only" | "persistent" | "intermittent" | "never_active";
};

type RoutingTimeline = {
  schema_version: number;
  created_at: string;
  label: string;
  source: {
    prompt_path: string;
    model: string;
    ctx: number;
    chunk_count: number;
    early_chunks: number;
    chunk_files: string[];
  };
  summary: {
    expert_count: number;
    early_only_count: number;
    late_only_count: number;
    intermittent_count: number;
    persistent_count: number;
    never_active_count: number;
    total_selections: number;
  };
  chunks: Array<{
    index: number;
    prompt_file: string;
    total_selections: number;
    zero_expert_slots: number;
    nonzero_expert_slots: number;
  }>;
  experts: RoutingTimelineExpert[];
  early_only_experts: RoutingTimelineExpert[];
  late_only_experts: RoutingTimelineExpert[];
  intermittent_experts: RoutingTimelineExpert[];
  note: string;
};

type EvictionCandidate = {
  id: string;
  layer: number;
  expert: number;
  timeline_count: number;
  active_runs: number;
  early_only_runs: number;
  later_active_runs: number;
  total_count: number;
  total_early_count: number;
  total_later_count: number;
  early_only_rate_active: number;
  later_share: number;
  decision: string;
  reason: string;
  trim_decision?: string | null;
  personal_classification?: string | null;
  early_only_labels: string[];
  later_active_labels: string[];
};

type RoutingTimelineSummary = {
  schema_version: number;
  created_at: string;
  source: {
    timeline_count: number;
    timeline_labels: string[];
  };
  summary: {
    expert_count: number;
    evict_after_prefix_candidate_count: number;
    evict_watchlist_tiny_later_count: number;
    never_active_in_timelines_count: number;
    keep_runtime_later_used_count: number;
  };
  evict_after_prefix_candidates: EvictionCandidate[];
  evict_watchlist_tiny_later: EvictionCandidate[];
  never_active_in_timelines: EvictionCandidate[];
  note: string;
};

type RoutingBundle = {
  schema_version: number;
  default_trace: string;
  traces: Record<string, RoutingTrace>;
  comparisons?: {
    reasoning_on_vs_off?: ReasoningComparison;
  };
};

type ViewMode = "shard" | "attention" | "offset" | "routing" | "cold";

const viewModes: { mode: ViewMode; label: string; icon: typeof Database }[] = [
  { mode: "shard", label: "Shard", icon: Database },
  { mode: "attention", label: "Attention", icon: Radar },
  { mode: "offset", label: "Packed offset", icon: SplitSquareVertical },
  { mode: "routing", label: "Routing", icon: Route },
  { mode: "cold", label: "Least used", icon: Snowflake },
];

const manifestUrl = "/data/expert_manifest.json";
const routingUrl = "/data/routing_trace.json";
const routingBundleUrl = "/data/routing_traces.json";
const themeBundleUrl = "/data/personal_agent_routing_traces.json";
const routingTimelineUrl = "/data/routing_timeline.json";
const routingTimelineSummaryUrl = "/data/routing_timeline_summary.json";

function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatCompact(value: number): string {
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatSignedPercent(value: number): string {
  const percent = value * 100;
  return `${percent >= 0 ? "+" : ""}${percent.toFixed(2)}pp`;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function labelFromKey(key: string): string {
  return key.replaceAll("_", " ");
}

function shortFile(file: string): string {
  return file.replace("model-", "shard ").replace("-of-00002.safetensors", "");
}

function cellColor(
  expert: ExpertRecord,
  mode: ViewMode,
  routing?: RoutingExpert,
  maxRoutingCount = 1,
  coldRank?: number,
): string {
  if (mode === "cold") {
    if (!routing) return "#1a2330";
    if (routing.count === 0) return "#f27070";
    if (coldRank !== undefined) {
      const t = Math.max(0, Math.min(1, 1 - coldRank / 384));
      const hue = 34 + t * 102;
      const light = 39 + t * 20;
      return `hsl(${hue}, 78%, ${light}%)`;
    }
    return expert.is_full_attention ? "#26313f" : "#182230";
  }

  if (mode === "routing") {
    if (!routing) return expert.is_full_attention ? "#334155" : "#26313f";
    const t = Math.max(0, Math.min(1, routing.count / Math.max(maxRoutingCount, 1)));
    const hue = 190 - t * 154;
    const light = 27 + t * 34;
    const saturation = 52 + t * 34;
    return `hsl(${hue}, ${saturation}%, ${light}%)`;
  }

  if (mode === "attention") {
    return expert.is_full_attention ? "#e0a33b" : "#3bb2d0";
  }

  if (mode === "offset") {
    const t = expert.expert / 127;
    const hue = 190 + t * 56;
    const light = 37 + t * 17;
    return `hsl(${hue}, 68%, ${light}%)`;
  }

  const key = expert.shards.join("+");
  if (key === "1") return "#4cc7b0";
  if (key === "2") return "#d79a51";
  return "#b7c96a";
}

function shardLabel(shards: number[]): string {
  return shards.length ? shards.map((shard) => `S${shard}`).join("+") : "unknown";
}

function AppShell({
  manifest,
  children,
}: {
  manifest: Manifest;
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Boxes size={20} strokeWidth={2.2} />
          </div>
          <div className="brand-copy">
            <div className="brand-meta">
              <span>Public research instrument</span>
              <span>Manifest v{manifest.schema_version}</span>
            </div>
            <h1>Gemma Expert Atlas</h1>
            <p>MoE tensor placement, routing sparsity, and eviction evidence for Gemma 4 26B A4B.</p>
          </div>
        </div>
        <div className="topbar-stats" aria-label="model summary">
          <StatPill label="Layers" value={manifest.model.num_hidden_layers.toString()} />
          <StatPill label="Experts/layer" value={manifest.model.num_experts.toString()} />
          <StatPill label="Top-k routes" value={manifest.model.top_k_experts.toString()} />
          <StatPill label="Weight set" value={manifest.model.human_total_size} />
          <StatPill label="Generated" value={formatTimestamp(manifest.generated_at)} />
        </div>
      </header>
      {children}
    </div>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-pill">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Sidebar({
  manifest,
  routingTrace,
  traceOptions,
  selectedTraceKey,
  setSelectedTraceKey,
  themeOptions,
  selectedThemeKey,
  setSelectedThemeKey,
  selectedThemeMode,
  setSelectedThemeMode,
  viewMode,
  setViewMode,
  layerFilter,
  setLayerFilter,
  shardFilter,
  setShardFilter,
}: {
  manifest: Manifest;
  routingTrace: RoutingTrace | null;
  traceOptions: string[];
  selectedTraceKey: string;
  setSelectedTraceKey: (value: string) => void;
  themeOptions: Array<{ key: string; label: string }>;
  selectedThemeKey: string;
  setSelectedThemeKey: (value: string) => void;
  selectedThemeMode: ThemeMode;
  setSelectedThemeMode: (value: ThemeMode) => void;
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  layerFilter: string;
  setLayerFilter: (value: string) => void;
  shardFilter: string;
  setShardFilter: (value: string) => void;
}) {
  const routedLayerCount = routingTrace?.summary.layers_with_counts ?? 0;

  return (
    <aside className="sidebar">
      <section className="panel summary-panel">
        <div className="panel-title">
          <Layers3 size={17} />
          <div>
            <h2>Evidence scope</h2>
            <p>Manifest, tensor slices, and trace coverage loaded from public data artifacts.</p>
          </div>
        </div>
        <dl className="summary-list">
          <div>
            <dt>Parameters</dt>
            <dd>{formatCompact(manifest.model.total_parameters)}</dd>
          </div>
          <div>
            <dt>Expert payload</dt>
            <dd>{manifest.summary.human_total_expert_group_bytes}</dd>
          </div>
          <div>
            <dt>Per expert</dt>
            <dd>{manifest.summary.human_per_expert_bytes}</dd>
          </div>
          <div>
            <dt>Split layers</dt>
            <dd>{manifest.summary.expert_layer_split_count}</dd>
          </div>
          <div>
            <dt>Route selections</dt>
            <dd>{routingTrace ? formatCompact(routingTrace.summary.total_selections) : "--"}</dd>
          </div>
          <div>
            <dt>Zero route slots</dt>
            <dd>{routingTrace ? routingTrace.summary.zero_expert_slots.toString() : "--"}</dd>
          </div>
        </dl>
        <div className="scope-status">
          <span>{routedLayerCount || "--"} routed layers</span>
          <span>{manifest.summary.tensor_count} tensors indexed</span>
        </div>
      </section>

      <section className="panel controls-panel">
        <div className="panel-title">
          <Activity size={17} />
          <div>
            <h2>Atlas lens</h2>
            <p>Switch the grid between placement, attention, routing, and cold-expert evidence.</p>
          </div>
        </div>
        <div className="segmented">
          {viewModes.map(({ mode, label, icon: Icon }) => (
            <button
              key={mode}
              className={viewMode === mode ? "is-active" : ""}
              onClick={() => setViewMode(mode)}
              type="button"
              aria-pressed={viewMode === mode}
            >
              <Icon size={15} />
              <span>{label}</span>
            </button>
          ))}
        </div>
        <label className="select-label">
          <span>Theme</span>
          <div className="select-wrap">
            <select
              data-testid="theme-select"
              value={selectedThemeKey}
              onChange={(event) => setSelectedThemeKey(event.target.value)}
            >
              <option value="overall">Overall</option>
              {themeOptions.map((theme) => (
                <option key={theme.key} value={theme.key}>
                  {theme.label}
                </option>
              ))}
            </select>
            <ChevronDown size={15} />
          </div>
        </label>
        {selectedThemeKey === "overall" ? (
          <label className="select-label">
            <span>Trace</span>
            <div className="select-wrap">
              <select
                data-testid="trace-select"
                value={selectedTraceKey}
                onChange={(event) => setSelectedTraceKey(event.target.value)}
              >
                {traceOptions.map((trace) => (
                  <option key={trace} value={trace}>
                    {labelFromKey(trace)}
                  </option>
                ))}
              </select>
              <ChevronDown size={15} />
            </div>
          </label>
        ) : (
          <label className="select-label">
            <span>Reasoning</span>
            <div className="select-wrap">
              <select
                data-testid="theme-mode-select"
                value={selectedThemeMode}
                onChange={(event) => setSelectedThemeMode(event.target.value as ThemeMode)}
              >
                <option value="reasoning_off">off</option>
                <option value="reasoning_on">on</option>
              </select>
              <ChevronDown size={15} />
            </div>
          </label>
        )}
        <label className="select-label">
          <span>Layer type</span>
          <div className="select-wrap">
            <select value={layerFilter} onChange={(event) => setLayerFilter(event.target.value)}>
              <option value="all">All layers</option>
              <option value="sliding_attention">Sliding attention</option>
              <option value="full_attention">Full attention</option>
            </select>
            <ChevronDown size={15} />
          </div>
        </label>
        <label className="select-label">
          <span>Shard</span>
          <div className="select-wrap">
            <select value={shardFilter} onChange={(event) => setShardFilter(event.target.value)}>
              <option value="all">All shards</option>
              <option value="1">Shard 1</option>
              <option value="2">Shard 2</option>
              <option value="split">Split experts</option>
            </select>
            <ChevronDown size={15} />
          </div>
        </label>
      </section>

      <section className="panel shard-panel">
        <div className="panel-title">
          <Database size={17} />
          <div>
            <h2>Weight files</h2>
            <p>Safetensor shards backing the selected expert slices.</p>
          </div>
        </div>
        <div className="shard-list">
          {manifest.shards.map((shard) => (
            <div className="shard-row" key={shard.file}>
              <div>
                <strong>{shortFile(shard.file)}</strong>
                <span>{shard.tensor_count} tensors</span>
              </div>
              <b>{shard.human_file_size}</b>
            </div>
          ))}
        </div>
      </section>
    </aside>
  );
}

function ExpertHeatmap({
  manifest,
  routingById,
  coldRankById,
  maxRoutingCount,
  viewMode,
  layerFilter,
  shardFilter,
  selectedId,
  onSelect,
}: {
  manifest: Manifest;
  routingById: Map<string, RoutingExpert>;
  coldRankById: Map<string, number>;
  maxRoutingCount: number;
  viewMode: ViewMode;
  layerFilter: string;
  shardFilter: string;
  selectedId: string;
  onSelect: (expert: ExpertRecord) => void;
}) {
  const [hover, setHover] = useState<{ expert: ExpertRecord; x: number; y: number } | null>(null);
  const cellW = 7.2;
  const cellH = 18;
  const labelW = 58;
  const topPad = 28;
  const bottomPad = 18;
  const width = labelW + manifest.model.num_experts * cellW;
  const height = topPad + manifest.model.num_hidden_layers * cellH + bottomPad;
  const currentLens = viewModes.find(({ mode }) => mode === viewMode)?.label ?? "Shard";
  const activeFilters = [
    layerFilter === "all" ? "all layers" : layerFilter.replace("_", " "),
    shardFilter === "all" ? "all shards" : shardFilter === "split" ? "split experts" : `shard ${shardFilter}`,
  ];
  const legend =
    viewMode === "cold"
      ? [
          ["legend-danger", "Zero routes"],
          ["legend-cold", "Bottom 10%"],
          ["legend-dim", "Other"],
        ]
      : [
          ["legend-cyan", "Shard 1"],
          ["legend-amber", "Shard 2"],
          ["legend-split", "Split"],
        ];
  const visible = (expert: ExpertRecord) => {
    if (layerFilter !== "all" && expert.layer_type !== layerFilter) return false;
    if (shardFilter === "split") return expert.is_split_across_shards;
    if (shardFilter !== "all") return expert.shards.includes(Number(shardFilter));
    return true;
  };

  return (
    <section className="atlas-panel">
      <div className="atlas-header">
        <div className="atlas-copy">
          <span className="section-kicker">Expert grid</span>
          <h2>30 layers x 128 routed experts</h2>
          <p>
            {manifest.summary.expert_record_count} packed slices across {manifest.summary.human_total_expert_group_bytes}; {activeFilters.join(" / ")}.
          </p>
        </div>
        <div className="atlas-tools">
          <span className="atlas-lens">{currentLens} lens</span>
          <div className="legend">
            {legend.map(([className, label]) => (
              <span key={label}>
                <i className={className} /> {label}
              </span>
            ))}
          </div>
        </div>
      </div>
      <div className="heatmap-scroll">
        <svg
          className="heatmap"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="Gemma MoE expert heatmap"
          onMouseLeave={() => setHover(null)}
        >
          <text className="axis-title" x={labelW} y={12}>
            layer
          </text>
          <text className="axis-title" x={labelW + 2} y={height - 3}>
            expert index
          </text>
          {Array.from({ length: 9 }).map((_, idx) => {
            const expert = idx * 16;
            return (
              <text className="axis-label" key={expert} x={labelW + expert * cellW} y={20} textAnchor="middle">
                {expert}
              </text>
            );
          })}
          {manifest.layers.map((layer) => {
            const y = topPad + layer.layer * cellH;
            return (
              <g key={layer.layer}>
                <text className="row-label" x={4} y={y + 11}>
                  {layer.layer_label}
                </text>
                <line className={layer.is_full_attention ? "row-rule row-rule-full" : "row-rule"} x1={labelW - 7} x2={width} y1={y + 15.5} y2={y + 15.5} />
              </g>
            );
          })}
          {manifest.experts.map((expert) => {
            const x = labelW + expert.expert * cellW;
            const y = topPad + expert.layer * cellH;
            const isSelected = expert.id === selectedId;
            const isVisible = visible(expert);
            const routing = routingById.get(expert.id);
            const coldRank = coldRankById.get(expert.id);
            return (
              <rect
                key={expert.id}
                className={isSelected ? "expert-cell is-selected" : "expert-cell"}
                x={x}
                y={y}
                width={cellW - 1.2}
                height={cellH - 3}
                rx={1.3}
                fill={cellColor(expert, viewMode, routing, maxRoutingCount, coldRank)}
                opacity={isVisible ? 1 : 0.13}
                onClick={() => onSelect(expert)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSelect(expert);
                  }
                }}
                onMouseMove={(event) => setHover({ expert, x: event.clientX, y: event.clientY })}
                role="button"
                tabIndex={0}
                aria-label={`${expert.id}, ${expert.layer_type.replace("_", " ")}, ${shardLabel(expert.shards)}`}
              />
            );
          })}
        </svg>
      </div>
      {hover ? (
        <div className="tooltip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
          <strong>{hover.expert.id}</strong>
          <span>{hover.expert.layer_type.replace("_", " ")}</span>
          <span>{shardLabel(hover.expert.shards)} - {hover.expert.human_total_bytes}</span>
          {routingById.get(hover.expert.id) ? (
            <span>
              {routingById.get(hover.expert.id)?.count} routes
              {coldRankById.has(hover.expert.id) ? " - cold set" : ""}
            </span>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

function Inspector({
  manifest,
  selected,
  routing,
  routingLayer,
}: {
  manifest: Manifest;
  selected: ExpertRecord;
  routing?: RoutingExpert;
  routingLayer?: RoutingLayer;
}) {
  const layer = manifest.layers[selected.layer];
  const tensors = layer.tensors;
  return (
    <aside className="inspector">
      <section className="panel selected-panel">
        <div className="panel-title">
          <Cpu size={17} />
          <div>
            <h2>Selected expert</h2>
            <p>Click any atlas cell or evidence row to inspect its tensor and routing record.</p>
          </div>
        </div>
        <div className="selected-readout">
          <span>{layer.layer_label} / expert {selected.expert}</span>
          <strong>{selected.id}</strong>
          <em>{routing ? `${formatCompact(routing.count)} route selections` : "routing trace pending"}</em>
        </div>
        <div className="selected-meta">
          <span>{selected.layer_type.replace("_", " ")}</span>
          <span>{shardLabel(selected.shards)}</span>
          <span>{selected.human_total_bytes}</span>
        </div>
        <dl className="detail-list">
          <div>
            <dt>Layer bytes</dt>
            <dd>{layer.human_bytes}</dd>
          </div>
          <div>
            <dt>Router</dt>
            <dd>{layer.router_human_bytes}</dd>
          </div>
          <div>
            <dt>Shared MLP</dt>
            <dd>{layer.shared_mlp_human_bytes}</dd>
          </div>
          <div>
            <dt>Expert split</dt>
            <dd>{selected.is_split_across_shards ? "yes" : "no"}</dd>
          </div>
          <div>
            <dt>Route share</dt>
            <dd>{routing ? `${(routing.share * 100).toFixed(2)}%` : "--"}</dd>
          </div>
          <div>
            <dt>Route rank</dt>
            <dd>{routing ? routing.rank : "--"}</dd>
          </div>
        </dl>
      </section>

      <section className="panel tensor-panel">
        <div className="panel-title">
          <SplitSquareVertical size={17} />
          <h2>Tensor slices</h2>
        </div>
        <TensorSlice title="gate_up" data={selected.gate_up_proj} />
        <TensorSlice title="down" data={selected.down_proj} />
        <TensorSummary title="router" tensor={tensors.router_proj} />
        <TensorSummary title="per-expert scale" tensor={tensors.router_per_expert_scale} />
      </section>

      <section className="panel routing-panel">
        <div className="panel-title">
          <Route size={17} />
          <div>
            <h2>{routing ? "Routing evidence" : "Routing pending"}</h2>
            <p>{routingLayer ? `${formatCompact(routingLayer.total_selections)} selections in this layer` : "No active trace for this layer yet."}</p>
          </div>
        </div>
        <div className="pending-grid">
          <div><span>Route count</span><b>{routing ? routing.count : "--"}</b></div>
          <div><span>Layer share</span><b>{routing ? `${(routing.share * 100).toFixed(2)}%` : "--"}</b></div>
          <div><span>Trace rank</span><b>{routing ? routing.rank : "--"}</b></div>
          <div><span>layer total</span><b>{routingLayer ? formatCompact(routingLayer.total_selections) : "--"}</b></div>
        </div>
      </section>
    </aside>
  );
}

function TensorSlice({
  title,
  data,
}: {
  title: string;
  data: ExpertRecord["gate_up_proj"];
}) {
  if (!data) return null;
  return (
    <div className="tensor-slice">
      <div>
        <strong>{title}</strong>
        <span>{shortFile(data.file)}</span>
      </div>
      <p>{data.shape.join(" x ")}</p>
      <code>{data.slice ? data.slice.relative_offsets.map(formatNumber).join(" .. ") : "n/a"}</code>
    </div>
  );
}

function TensorSummary({ title, tensor }: { title: string; tensor?: TensorInfo }) {
  if (!tensor) return null;
  return (
    <div className="tensor-slice compact">
      <div>
        <strong>{title}</strong>
        <span>{shortFile(tensor.file)}</span>
      </div>
      <p>{tensor.shape.join(" x ")} - {tensor.human_bytes}</p>
    </div>
  );
}

function BottomCharts({ manifest, routingTrace }: { manifest: Manifest; routingTrace: RoutingTrace | null }) {
  const maxLayerBytes = Math.max(...manifest.layers.map((layer) => layer.bytes));
  const totalShardBytes = manifest.shards.reduce((sum, shard) => sum + shard.file_size, 0);
  const topPatterns = manifest.tensor_patterns.slice(0, 8);

  return (
    <section className="bottom-grid">
      <div className="chart-panel">
        <div className="chart-head">
          <h2>Layer footprint</h2>
          <span>{manifest.summary.human_total_layer_bytes}</span>
        </div>
        <div className="layer-bars">
          {manifest.layers.map((layer) => (
            <div className="layer-bar" key={layer.layer} title={`${layer.layer_label}: ${layer.human_bytes}`}>
              <span
                className={layer.is_full_attention ? "bar-fill full" : "bar-fill"}
                style={{ height: `${Math.max(8, (layer.bytes / maxLayerBytes) * 100)}%` }}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="chart-panel">
        <div className="chart-head">
          <h2>Shard placement</h2>
          <span>{manifest.summary.shard_count} files</span>
        </div>
        <div className="shard-bars">
          {manifest.shards.map((shard) => (
            <div className="shard-meter" key={shard.file}>
              <div className="meter-label">
                <strong>{shortFile(shard.file)}</strong>
                <span>{shard.human_file_size}</span>
              </div>
              <div className="meter-track">
                <span style={{ width: `${(shard.file_size / totalShardBytes) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="chart-panel">
        <div className="chart-head">
          <h2>{routingTrace ? "Top routed experts" : "Tensor families"}</h2>
          <span>{routingTrace ? `${routingTrace.summary.layers_with_counts} routed layers` : `${manifest.summary.tensor_count} tensors`}</span>
        </div>
        {routingTrace ? (
          <div className="pattern-list">
            {routingTrace.hot_experts.slice(0, 8).map((expert) => (
              <div className="pattern-row" key={expert.id}>
                <span>{expert.count}</span>
                <code>{expert.id} - {(expert.share * 100).toFixed(2)}% of layer routes</code>
              </div>
            ))}
          </div>
        ) : (
          <div className="pattern-list">
            {topPatterns.map((pattern) => (
              <div className="pattern-row" key={pattern.pattern}>
                <span>{pattern.count}</span>
                <code>{pattern.pattern}</code>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function RoutingStrip({ routingTrace }: { routingTrace: RoutingTrace | null }) {
  if (!routingTrace) {
    return null;
  }
  const max = Math.max(...routingTrace.layers.map((layer) => layer.max_count));
  return (
    <section className="routing-strip">
      <div>
        <h2>Trace coverage{routingTrace.label ? `: ${routingTrace.label.replaceAll("_", " ")}` : ""}</h2>
        <p>
          {formatCompact(routingTrace.summary.total_selections)} selections from {routingTrace.source.chunk_count} chunk
          {routingTrace.source.chunk_count === 1 ? "" : "s"} at {routingTrace.source.chunk_size} tokens
        </p>
      </div>
      <div className="routing-layer-bars">
        {routingTrace.layers.map((layer) => (
          <div className="routing-layer" key={layer.layer} title={`${layer.layer_label}: max ${layer.max_count}, zero ${layer.zero_experts}`}>
            <span style={{ height: `${Math.max(8, (layer.max_count / Math.max(max, 1)) * 100)}%` }} />
          </div>
        ))}
      </div>
    </section>
  );
}

function LeastUsedExperts({
  routingTrace,
  onSelect,
}: {
  routingTrace: RoutingTrace | null;
  onSelect: (id: string) => void;
}) {
  const least = useMemo(() => {
    if (!routingTrace) {
      return { zero: [], nonzero: [], layers: [] };
    }
    const sorted = [...routingTrace.experts].sort(
      (a, b) => a.count - b.count || a.layer - b.layer || a.expert - b.expert,
    );
    return {
      zero: sorted.filter((expert) => expert.count === 0).slice(0, 10),
      nonzero: sorted.filter((expert) => expert.count > 0).slice(0, 10),
      layers: [...routingTrace.layers]
        .sort((a, b) => b.zero_experts - a.zero_experts || a.layer - b.layer)
        .slice(0, 6),
    };
  }, [routingTrace]);

  if (!routingTrace) return null;

  return (
    <section className="least-used" data-testid="least-used">
      <div className="chart-head">
        <h2>Least used experts</h2>
        <span>{routingTrace.summary.zero_expert_slots} zero slots</span>
      </div>
      <div className="least-grid">
        <div className="least-column">
          <h3>Zero route</h3>
          <div className="least-list">
            {least.zero.length ? (
              least.zero.map((expert) => (
                <ColdExpertRow expert={expert} key={expert.id} label="zero" onSelect={onSelect} />
              ))
            ) : (
              <p>No zero-count experts in this trace.</p>
            )}
          </div>
        </div>
        <div className="least-column">
          <h3>Coldest nonzero</h3>
          <div className="least-list">
            {least.nonzero.map((expert) => (
              <ColdExpertRow expert={expert} key={expert.id} label={`${(expert.share * 100).toFixed(2)}%`} onSelect={onSelect} />
            ))}
          </div>
        </div>
        <div className="least-column">
          <h3>Sparsest layers</h3>
          <div className="least-list">
            {least.layers.map((layer) => (
              <div className="least-layer-row" key={layer.layer}>
                <strong>{layer.layer_label}</strong>
                <span>{layer.zero_experts} zero</span>
                <code>{layer.nonzero_experts} used</code>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function TimelineExperts({
  routingTimeline,
  onSelect,
}: {
  routingTimeline: RoutingTimeline | null;
  onSelect: (id: string) => void;
}) {
  if (!routingTimeline) {
    return (
      <section className="timeline-panel is-empty" data-testid="timeline-panel">
        <div className="chart-head">
          <h2>Early-only experts</h2>
          <span>timeline pending</span>
        </div>
        <p>Run the routing timeline capture to separate startup-only experts from truly cold experts.</p>
      </section>
    );
  }

  const topEarly = routingTimeline.early_only_experts.slice(0, 10);
  const topLate = routingTimeline.late_only_experts.slice(0, 6);

  return (
    <section className="timeline-panel" data-testid="timeline-panel">
      <div className="chart-head">
        <h2>Early-only experts</h2>
        <span>
          {routingTimeline.summary.early_only_count} early-only / {routingTimeline.source.chunk_count} chunks
        </span>
      </div>
      <div className="timeline-grid">
        <div className="timeline-column main">
          <h3>Loaded first, then gone</h3>
          <div className="timeline-list">
            {topEarly.length ? (
              topEarly.map((expert) => (
                <TimelineExpertRow expert={expert} key={expert.id} onSelect={onSelect} />
              ))
            ) : (
              <p>No early-only experts in this timeline.</p>
            )}
          </div>
        </div>
        <div className="timeline-column">
          <h3>Late-only contrast</h3>
          <div className="timeline-list compact">
            {topLate.map((expert) => (
              <TimelineExpertRow expert={expert} key={expert.id} onSelect={onSelect} />
            ))}
          </div>
        </div>
        <div className="timeline-summary">
          <div>
            <span>Source</span>
            <strong>{labelFromKey(routingTimeline.label)}</strong>
          </div>
          <div>
            <span>Early window</span>
            <strong>{routingTimeline.source.early_chunks} chunk</strong>
          </div>
          <div>
            <span>Intermittent</span>
            <strong>{routingTimeline.summary.intermittent_count}</strong>
          </div>
          <div>
            <span>Never active</span>
            <strong>{routingTimeline.summary.never_active_count}</strong>
          </div>
        </div>
      </div>
    </section>
  );
}

function RuntimeEvictionCandidates({
  summary,
  onSelect,
}: {
  summary: RoutingTimelineSummary | null;
  onSelect: (id: string) => void;
}) {
  if (!summary) return null;

  const topEvict = summary.evict_after_prefix_candidates.slice(0, 12);
  const topNever = summary.never_active_in_timelines.slice(0, 6);

  return (
    <section className="evict-panel" data-testid="evict-panel">
      <div className="chart-head">
        <h2>After-prefix eviction candidates</h2>
        <span>
          {summary.summary.evict_after_prefix_candidate_count} clean / {summary.source.timeline_count} timelines
        </span>
      </div>
      <div className="evict-grid">
        <div className="evict-column main">
          <h3>Early, then silent</h3>
          <div className="evict-list">
            {topEvict.map((candidate) => (
              <EvictionCandidateRow
                candidate={candidate}
                key={candidate.id}
                timelineCount={summary.source.timeline_count}
                tone="evict"
                onSelect={onSelect}
              />
            ))}
          </div>
        </div>
        <div className="evict-column">
          <h3>Never-active contrast</h3>
          <div className="evict-list compact">
            {topNever.map((candidate) => (
              <EvictionCandidateRow
                candidate={candidate}
                key={candidate.id}
                timelineCount={summary.source.timeline_count}
                tone="never"
                onSelect={onSelect}
              />
            ))}
          </div>
        </div>
        <div className="evict-summary">
          <div>
            <span>Clean candidates</span>
            <strong>{summary.summary.evict_after_prefix_candidate_count}</strong>
          </div>
          <div>
            <span>Later routes</span>
            <strong>{summary.evict_after_prefix_candidates.reduce((sum, item) => sum + item.total_later_count, 0)}</strong>
          </div>
          <div>
            <span>Never active</span>
            <strong>{summary.summary.never_active_in_timelines_count}</strong>
          </div>
          <div>
            <span>Runtime keep</span>
            <strong>{formatCompact(summary.summary.keep_runtime_later_used_count)}</strong>
          </div>
        </div>
      </div>
    </section>
  );
}

function EvictionCandidateRow({
  candidate,
  timelineCount,
  tone,
  onSelect,
}: {
  candidate: EvictionCandidate;
  timelineCount: number;
  tone: "evict" | "never";
  onSelect: (id: string) => void;
}) {
  const bars = Math.max(1, timelineCount);
  const className = tone === "evict" ? "evict-row" : "evict-row is-never";
  const label = candidate.personal_classification ?? candidate.trim_decision ?? candidate.decision;
  const count = tone === "evict" ? candidate.total_early_count : candidate.total_count;
  const runLabel = tone === "evict" ? `${candidate.early_only_runs}/${candidate.active_runs}` : `${candidate.active_runs}/${bars}`;
  return (
    <button
      className={className}
      data-expert-id={candidate.id}
      onClick={() => onSelect(candidate.id)}
      title={candidate.reason}
      type="button"
    >
      <strong>{candidate.id}</strong>
      <span className="confidence-bars" aria-label={`${candidate.id} timeline coverage`}>
        {Array.from({ length: bars }).map((_, index) => (
          <i
            className={index < candidate.early_only_runs ? "is-hit" : ""}
            key={`${candidate.id}-${index}`}
          />
        ))}
      </span>
      <span>{formatCompact(count)}</span>
      <span>{runLabel}</span>
      <code>{labelFromKey(label)}</code>
    </button>
  );
}

function TimelineExpertRow({
  expert,
  onSelect,
}: {
  expert: RoutingTimelineExpert;
  onSelect: (id: string) => void;
}) {
  const max = Math.max(1, ...expert.chunk_counts);
  const displayCount = expert.status === "early_only" ? expert.early_count : expert.total_count;
  return (
    <button className="timeline-row" data-expert-id={expert.id} onClick={() => onSelect(expert.id)} type="button">
      <strong>{expert.id}</strong>
      <span className="spark-bars" aria-label={`${expert.id} chunk activation`}>
        {expert.chunk_counts.map((count, index) => (
          <i
            className={index === expert.first_active_chunk ? "is-first" : ""}
            key={`${expert.id}-${index}`}
            style={{ height: `${Math.max(3, (count / max) * 100)}%`, opacity: count > 0 ? 1 : 0.22 }}
          />
        ))}
      </span>
      <span>{formatCompact(displayCount)}</span>
      <code>{expert.status.replace("_", " ")}</code>
    </button>
  );
}

function ColdExpertRow({
  expert,
  label,
  onSelect,
}: {
  expert: RoutingExpert;
  label: string;
  onSelect: (id: string) => void;
}) {
  return (
    <button className="least-row" data-expert-id={expert.id} onClick={() => onSelect(expert.id)} type="button">
      <strong>{expert.id}</strong>
      <span>{expert.count}</span>
      <code>{label}</code>
    </button>
  );
}

function ReasoningShift({
  comparison,
  title = "Reasoning shift",
  subtitle = "on vs off",
  onSelect,
}: {
  comparison?: ReasoningComparison;
  title?: string;
  subtitle?: string;
  onSelect: (id: string) => void;
}) {
  if (!comparison) return null;

  const onItems = comparison.top_reasoning_on.slice(0, 6);
  const offItems = comparison.top_reasoning_off.slice(0, 6);
  const maxDelta = Math.max(1, ...[...onItems, ...offItems].map((item) => Math.abs(item.delta_count)));

  return (
    <section className="reasoning-shift" data-testid="reasoning-shift">
      <div className="chart-head">
        <h2>{title}</h2>
        <span>{subtitle}</span>
      </div>
      <div className="shift-columns">
        <ShiftColumn title="More reasoning-on" tone="on" items={onItems} maxDelta={maxDelta} onSelect={onSelect} />
        <ShiftColumn title="More reasoning-off" tone="off" items={offItems} maxDelta={maxDelta} onSelect={onSelect} />
      </div>
    </section>
  );
}

function ShiftColumn({
  title,
  tone,
  items,
  maxDelta,
  onSelect,
}: {
  title: string;
  tone: "on" | "off";
  items: RoutingComparisonExpert[];
  maxDelta: number;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="shift-column">
      <h3>{title}</h3>
      <div className="shift-list">
        {items.map((item) => (
          <button
            className="shift-row"
            data-expert-id={item.id}
            key={item.id}
            onClick={() => onSelect(item.id)}
            type="button"
          >
            <strong>{item.id}</strong>
            <span className={`shift-bar ${tone}`}>
              <i style={{ width: `${Math.max(4, (Math.abs(item.delta_count) / maxDelta) * 100)}%` }} />
            </span>
            <span>{`${item.delta_count >= 0 ? "+" : ""}${formatCompact(item.delta_count)}`}</span>
            <code>{formatSignedPercent(item.delta_share)}</code>
          </button>
        ))}
      </div>
    </div>
  );
}

function ThemeMatrix({
  themeBundle,
  selectedThemeKey,
  onSelectTheme,
}: {
  themeBundle: ThemeBundle | null;
  selectedThemeKey: string;
  onSelectTheme: (theme: string) => void;
}) {
  if (!themeBundle) return null;

  const summaries = Object.entries(themeBundle.themes).map(([theme, info]) => {
    const off = themeBundle.traces[theme]?.reasoning_off;
    const on = themeBundle.traces[theme]?.reasoning_on;
    const comparison = themeBundle.comparisons[theme];
    return {
      key: theme,
      label: info.label,
      offZero: off?.summary.zero_expert_slots ?? 0,
      onZero: on?.summary.zero_expert_slots ?? 0,
      topOn: comparison?.top_reasoning_on[0],
      topOff: comparison?.top_reasoning_off[0],
    };
  });
  const maxZero = Math.max(1, ...summaries.flatMap((summary) => [summary.offZero, summary.onZero]));

  return (
    <section className="theme-matrix" data-testid="theme-matrix">
      <div className="chart-head">
        <h2>Theme map</h2>
        <span>{themeBundle.summary.theme_count} paired themes</span>
      </div>
      <div className="theme-table">
        {summaries.map((summary) => (
          <button
            className={selectedThemeKey === summary.key ? "theme-row is-active" : "theme-row"}
            data-theme-key={summary.key}
            key={summary.key}
            onClick={() => onSelectTheme(summary.key)}
            type="button"
          >
            <strong>{summary.label}</strong>
            <span className="zero-bars">
              <i className="zero-off" style={{ width: `${Math.max(4, (summary.offZero / maxZero) * 100)}%` }} />
              <i className="zero-on" style={{ width: `${Math.max(4, (summary.onZero / maxZero) * 100)}%` }} />
            </span>
            <span>{summary.offZero} off</span>
            <span>{summary.onZero} on</span>
            <code>{summary.topOn ? `${summary.topOn.id} ${formatSignedPercent(summary.topOn.delta_share)}` : "--"}</code>
            <code>{summary.topOff ? `${summary.topOff.id} ${formatSignedPercent(summary.topOff.delta_share)}` : "--"}</code>
          </button>
        ))}
      </div>
    </section>
  );
}

function LoadingState() {
  return (
    <main className="loading-state">
      <div className="loading-card">
        <Boxes size={28} />
        <h1>Expert Atlas</h1>
        <p>Loading manifest</p>
      </div>
    </main>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <main className="loading-state">
      <div className="loading-card error">
        <h1>Manifest unavailable</h1>
        <p>{message}</p>
      </div>
    </main>
  );
}

export function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [routingTrace, setRoutingTrace] = useState<RoutingTrace | null>(null);
  const [routingBundle, setRoutingBundle] = useState<RoutingBundle | null>(null);
  const [themeBundle, setThemeBundle] = useState<ThemeBundle | null>(null);
  const [routingTimeline, setRoutingTimeline] = useState<RoutingTimeline | null>(null);
  const [routingTimelineSummary, setRoutingTimelineSummary] = useState<RoutingTimelineSummary | null>(null);
  const [selectedTraceKey, setSelectedTraceKey] = useState("mixed");
  const [selectedThemeKey, setSelectedThemeKey] = useState("overall");
  const [selectedThemeMode, setSelectedThemeMode] = useState<ThemeMode>("reasoning_on");
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("shard");
  const [layerFilter, setLayerFilter] = useState("all");
  const [shardFilter, setShardFilter] = useState("all");
  const [selectedId, setSelectedId] = useState("L00.E000");

  useEffect(() => {
    fetch(manifestUrl)
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
        return response.json();
      })
      .then((data: Manifest) => setManifest(data))
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    fetch(routingBundleUrl)
      .then((response) => {
        if (!response.ok) return null;
        return response.json();
      })
      .then((data: RoutingBundle | null) => {
        setRoutingBundle(data);
        if (data?.default_trace) setSelectedTraceKey(data.default_trace);
      })
      .catch(() => setRoutingBundle(null));
  }, []);

  useEffect(() => {
    fetch(routingUrl)
      .then((response) => {
        if (!response.ok) return null;
        return response.json();
      })
      .then((data: RoutingTrace | null) => setRoutingTrace(data))
      .catch(() => setRoutingTrace(null));
  }, []);

  useEffect(() => {
    fetch(themeBundleUrl)
      .then((response) => {
        if (!response.ok) return null;
        return response.json();
      })
      .then((data: ThemeBundle | null) => setThemeBundle(data))
      .catch(() => setThemeBundle(null));
  }, []);

  useEffect(() => {
    fetch(routingTimelineUrl)
      .then((response) => {
        if (!response.ok) return null;
        return response.json();
      })
      .then((data: RoutingTimeline | null) => setRoutingTimeline(data))
      .catch(() => setRoutingTimeline(null));
  }, []);

  useEffect(() => {
    fetch(routingTimelineSummaryUrl)
      .then((response) => {
        if (!response.ok) return null;
        return response.json();
      })
      .then((data: RoutingTimelineSummary | null) => setRoutingTimelineSummary(data))
      .catch(() => setRoutingTimelineSummary(null));
  }, []);

  const activeThemeTrace =
    selectedThemeKey === "overall" ? null : themeBundle?.traces[selectedThemeKey]?.[selectedThemeMode] ?? null;
  const activeRoutingTrace = activeThemeTrace ?? routingBundle?.traces[selectedTraceKey] ?? routingTrace;
  const traceOptions = routingBundle ? Object.keys(routingBundle.traces) : routingTrace ? [routingTrace.label ?? "mixed"] : ["pending"];
  const themeOptions = themeBundle
    ? Object.entries(themeBundle.themes).map(([key, theme]) => ({ key, label: theme.label }))
    : [];
  const activeComparison =
    selectedThemeKey === "overall"
      ? routingBundle?.comparisons?.reasoning_on_vs_off
      : themeBundle?.comparisons[selectedThemeKey];
  const activeComparisonTitle =
    selectedThemeKey === "overall" ? "Reasoning shift" : `${labelFromKey(selectedThemeKey)} shift`;

  const selected = useMemo(() => {
    if (!manifest) return null;
    return manifest.experts.find((expert) => expert.id === selectedId) ?? manifest.experts[0];
  }, [manifest, selectedId]);

  const routingById = useMemo(() => {
    const map = new Map<string, RoutingExpert>();
    activeRoutingTrace?.experts.forEach((expert) => map.set(expert.id, expert));
    return map;
  }, [activeRoutingTrace]);

  const routingLayersByIndex = useMemo(() => {
    const map = new Map<number, RoutingLayer>();
    activeRoutingTrace?.layers.forEach((layer) => map.set(layer.layer, layer));
    return map;
  }, [activeRoutingTrace]);

  const coldRankById = useMemo(() => {
    const map = new Map<string, number>();
    if (!activeRoutingTrace) return map;
    const coldLimit = Math.ceil(activeRoutingTrace.experts.length * 0.1);
    [...activeRoutingTrace.experts]
      .sort((a, b) => a.count - b.count || a.layer - b.layer || a.expert - b.expert)
      .slice(0, coldLimit)
      .forEach((expert, index) => map.set(expert.id, index));
    return map;
  }, [activeRoutingTrace]);

  if (error) return <ErrorState message={error} />;
  if (!manifest || !selected) return <LoadingState />;

  const selectedRouting = routingById.get(selected.id);
  const selectedRoutingLayer = routingLayersByIndex.get(selected.layer);
  const maxRoutingCount = activeRoutingTrace?.summary.max_count ?? 1;

  return (
    <AppShell manifest={manifest}>
      <main className="workspace">
        <Sidebar
          manifest={manifest}
          routingTrace={activeRoutingTrace}
          traceOptions={traceOptions}
          selectedTraceKey={routingBundle ? selectedTraceKey : traceOptions[0]}
          setSelectedTraceKey={setSelectedTraceKey}
          themeOptions={themeOptions}
          selectedThemeKey={selectedThemeKey}
          setSelectedThemeKey={setSelectedThemeKey}
          selectedThemeMode={selectedThemeMode}
          setSelectedThemeMode={setSelectedThemeMode}
          viewMode={viewMode}
          setViewMode={setViewMode}
          layerFilter={layerFilter}
          setLayerFilter={setLayerFilter}
          shardFilter={shardFilter}
          setShardFilter={setShardFilter}
        />
        <section className="center-stack">
          <ExpertHeatmap
            manifest={manifest}
            routingById={routingById}
            coldRankById={coldRankById}
            maxRoutingCount={maxRoutingCount}
            viewMode={viewMode}
            layerFilter={layerFilter}
            shardFilter={shardFilter}
            selectedId={selected.id}
            onSelect={(expert) => setSelectedId(expert.id)}
          />
          <RoutingStrip routingTrace={activeRoutingTrace} />
          <LeastUsedExperts routingTrace={activeRoutingTrace} onSelect={setSelectedId} />
          <RuntimeEvictionCandidates summary={routingTimelineSummary} onSelect={setSelectedId} />
          <TimelineExperts routingTimeline={routingTimeline} onSelect={setSelectedId} />
          <ReasoningShift
            comparison={activeComparison}
            title={activeComparisonTitle}
            subtitle={selectedThemeKey === "overall" ? "overall on vs off" : `${selectedThemeMode.replace("_", " ")}`}
            onSelect={setSelectedId}
          />
          <ThemeMatrix themeBundle={themeBundle} selectedThemeKey={selectedThemeKey} onSelectTheme={setSelectedThemeKey} />
          <BottomCharts manifest={manifest} routingTrace={activeRoutingTrace} />
        </section>
        <Inspector
          manifest={manifest}
          selected={selected}
          routing={selectedRouting}
          routingLayer={selectedRoutingLayer}
        />
      </main>
    </AppShell>
  );
}
