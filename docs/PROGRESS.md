# main-core 项目进度总览

> 任务源：`docs/TASK_BREAKDOWN.md`
> 项目文档：`docs/main-core.project-doc.md` (v0.1.2)
> 更新日期：2026-05-11
> 当前基线：`origin/main` = `471dcf5` (`Merge pull request #66 from shenfanjie5-bit/mvp20-decision-pool`)

## 当前结论

`main-core` 仓库内已有 L1-L8 实现、formal object schema、public entrypoints、
MVP20 fixed decision pool、CI workflow 和测试覆盖。

本进度页只描述 `main-core` 仓库内已落地状态；不声明 production rollout complete。
下游 orchestrator 的 pin/path 更新与接入验证仍由 orchestrator 后续变更处理，不在
`main-core` 内完成。

## 里程碑总览

| Milestone | 名称 | 对应项目文档 | 状态 | 说明 |
|-----------|------|------------|------|------|
| milestone-0 | 包骨架与 formal 对象基线 | §25.2 第 1 步 | done | `src/main_core` 包、L1-L8 子包、`common` schemas/protocols/types/errors、边界测试已落地。 |
| milestone-1 | P2a 纯数据骨架 (L1-L3) | §21 阶段 0 / §25.2 第 2 步 | done | L1/L2 models/readers 与 L3 feature builder、multiplier store/API、graph/candidate signal adapters 已实现并有测试。 |
| milestone-2 | P2b L4-L7 正式判断链 | §21 阶段 1 / §25.2 第 3 步 | done | L4 world state、L5 universe/freezer/service、L6 analyzers/fallback、L7 recommendation/override/constraints 已实现并有测试。 |
| milestone-3 | P2c 发布与审计对接 | §21 阶段 2 / §25.2 第 4 步 | done-in-core | L8 publish assembler、manifest、dashboard、report、audit payload helpers 已在 `main-core` 内实现并测试；生产发布 rollout 不由本仓库声明完成。 |
| milestone-4 | P3-P5 图谱与子系统接入 | §21 阶段 3 | implemented-in-core | graph snapshot / graph impact snapshot 的只读 adapter 与 Layer B candidate signals 已在 `main-core` 侧实现并有 integration tests；外部系统 pin/path 接入仍属下游后续工作。 |
| milestone-5 | P8 MultiAgent 选项 | §21 阶段 4 / §16.3 | implemented-in-core | `MultiAgentAnalyzer` 与 A/B runner 已实现并有测试；默认/生产切换策略不在本进度页声明完成。 |
| MVP20 | fixed decision pool | PR #66 | done | `main_core.l5_universe.mvp20` 已落地；L5 只从 20 个 manifest targets 形成 official pool，related entities 不参与 L7 eligibility。 |

## Issue 状态明细

| Issue | 标题 | Milestone | Priority | 当前状态 | 证据 |
|-------|------|-----------|----------|----------|------|
| ISSUE-001 | 搭建 main-core 单项目强 package 骨架与边界静态检查 | milestone-0 | P0 | done | `src/main_core/l*_*/`、`tests/test_package_boundaries.py`、`tests/boundary/` |
| ISSUE-002 | 定义六类 formal object 与运行时 bundle 的 Pydantic schema | milestone-0 | P0 | done | `src/main_core/common/schemas/`、`tests/schemas/`、`tests/contract/` |
| ISSUE-003 | 定义 AnalyzerInterface / WorldStatePolicy / RecommendationConstraintProvider 三类协议接口 | milestone-0 | P0 | done | `src/main_core/common/protocols/`、`tests/protocols/` |
| ISSUE-004 | 实现 l1_l2_basis 基础数据读取层 | milestone-1 | P0 | done | `src/main_core/l1_l2_basis/`、`tests/l1_l2_basis/` |
| ISSUE-005 | 实现 l3_features 特征/信号主干与 feature_weight_multiplier 在线写入 | milestone-1 | P0 | done | `src/main_core/l3_features/`、`tests/l3_features/`、`tests/integration/test_l1_l3_feature_flow.py` |
| ISSUE-006 | 实现 l4_world_state 混合驱动共享状态 | milestone-2 | P0 | done | `src/main_core/l4_world_state/`、`tests/l4_world_state/` |
| ISSUE-007 | 实现 l5_universe 正式池选择与冻结 | milestone-2 | P0 | done | `src/main_core/l5_universe/`、`tests/l5_universe/` |
| ISSUE-008 | 实现 l6_alpha SinglePromptAnalyzer 与 inconclusive 降级 | milestone-2 | P0 | done | `src/main_core/l6_alpha/`、`tests/l6_alpha/` |
| ISSUE-009 | 实现 l7_recommendation 正式建议、override 与 constraint gate | milestone-2 | P0 | done | `src/main_core/l7_recommendation/`、`tests/l7_recommendation/` |
| ISSUE-010 | 实现 l8_publish 发布装配与 manifest 发起 | milestone-3 | P0 | done-in-core | `src/main_core/l8_publish/assembler.py`、`manifest.py`、`tests/l8_publish/` |
| ISSUE-011 | 实现 dashboard_snapshot 与 formal report 的正式业务内容 | milestone-3 | P1 | done-in-core | `src/main_core/l8_publish/dashboard.py`、`report.py`、`tests/l8_publish/test_dashboard.py`、`test_report.py` |
| ISSUE-012 | 接入 graph_snapshot 与 graph_impact_snapshot 只读消费 | milestone-4 | P1 | implemented-in-core | `graph_adapter.py`、`tests/integration/test_graph_readonly_consumption.py` |
| ISSUE-013 | 接入 Layer B 候选信号到 l3_features | milestone-4 | P1 | implemented-in-core | `candidate_signals.py`、`tests/integration/test_layer_b_candidate_signals.py` |
| ISSUE-014 | 实现 MultiAgentAnalyzer 与 A/B 评估脚本 | milestone-5 | P2 | implemented-in-core | `multi_agent_analyzer.py`、`ab_runner.py`、`tests/l6_alpha/test_multi_agent_analyzer.py`、`test_ab_runner.py` |

## MVP20 状态

MVP20 fixed decision pool 已合入 `main`：

- PR: `#66`
- Merge SHA: `471dcf5e53a38d5be8bbb79113af061fd4e3b462`
- 入口：`main_core.l5_universe.select_mvp20_decision_pool`
- 规则：manifest targets 必须恰好 20 个；所有 targets 必须在当前
  `FeatureSignalBundle` 输入中；related entities 可作为上下文输入，但不能进入
  L5 selected entities 或下游 L7 eligibility。
- 覆盖：`tests/l5_universe/test_mvp20.py`

## Public entrypoints 与验证面

`src/main_core/public.py` 提供 assembly-compatible 入口：

- `health_probe`
- `smoke_hook`
- `init_hook`
- `version_declaration`
- `cli`

最小公开入口验证：

```bash
PYTHONPATH=src python3 -m pytest -q tests/l5_universe/test_mvp20.py \
  tests/unit/test_public_entrypoints.py \
  tests/smoke/test_public_smoke.py
```

CI workflow 也已存在：

- full `python -m pytest`
- `make test-fast`
- `make smoke`
- `make regression`
- `python -m pytest tests/contract -q`

## §23 验收对照

| 验收条目 | 当前状态 | 证据 |
|----------|----------|------|
| 纯市场数据最小 L1-L8 闭环跑通 | implemented/tested in core | L1/L2、L3、L4、L5、L6、L7、L8 单元与集成测试 |
| 六类主业务 formal object 定义与生成路径 | implemented/tested | `common/schemas/`、各 L 层 service、`tests/schemas/`、`tests/l8_publish/` |
| `feature_weight_multiplier` 在 `l3_features` 生效 | implemented/tested | `multiplier_store.py`、`weight_api.py`、`tests/l3_features/` |
| Phase 3 发布走 manifest 且禁止用上一轮顶替 | implemented/tested in core | `l8_publish/manifest.py`、`tests/l8_publish/test_manifest.py` |
| OWN/BAN 边界与主项目一致 | tested | `tests/test_package_boundaries.py`、`tests/boundary/` |

## 仍未由本仓库完成的事项

1. Production rollout complete 不由 `main-core` 单仓库声明；需要结合 downstream
   orchestrator、module registry、deployment/runtime 验证一起确认。
2. Orchestrator 的 dependency pin/path 更新、registry 指向、集成流水线调整属于
   orchestrator 后续 PR，不在 `main-core` 内完成。
3. 外部模块的真实运行时依赖仍按 OWN/BAN 边界处理：数据库归 data-platform，
   LLM/runtime 归 reasoner-runtime，审计/回放归 audit-eval，图数据库归 graph-engine。
4. MultiAgent 是否作为默认生产 analyzer、以及 A/B 评估后的切换策略，仍需由上层
   rollout/decision 流程明确。

## 下一步

1. 在 orchestrator 仓库后续更新 `main-core` 的 pin/path，并运行对应 assembly
   集成验证。
2. 保持 `main-core` 内的最小验证命令与 CI lanes 通过。
3. 如生产 rollout 需要更多证据，在 rollout PR 中引用 CI、orchestrator 集成结果、
   registry diff 和运行时 smoke 结果，而不是仅引用本进度页。
