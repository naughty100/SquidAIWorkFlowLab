# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false
"""显式 StateGraph 的节点、条件边和纯 interrupt 节点。"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ai_workflow_lab.capabilities import StructuredOutputMethod
from ai_workflow_lab.config import LabSettings
from ai_workflow_lab.exp01.capability import freeze_native_method
from ai_workflow_lab.exp02.budget import ExecutionBudget
from ai_workflow_lab.exp02.domain import (
    ProposalBundle,
    ProposalDraft,
    ResearchFinding,
    ResearchPack,
    SourceEvidence,
)
from ai_workflow_lab.exp02.execution import Experiment02Mode, run_fixed_research
from ai_workflow_lab.exp02.finalizer import (
    FixtureProposalBackend,
    OpenAIProposalBackend,
    ProposalBackend,
    finalize_proposal,
    render_proposal_markdown,
)
from ai_workflow_lab.exp02.tools import FixtureWebTools, TavilyWebTools, load_fixture
from ai_workflow_lab.exp04.domain import DocumentChunk, RetrievalProfile
from ai_workflow_lab.exp04.evaluation import load_retrieval_cases
from ai_workflow_lab.exp04.indexing import (
    HashEmbeddings,
    RagIndex,
    load_documents,
    load_embedding_profile,
)
from ai_workflow_lab.run_recording import RunRecorder

from .domain import WorkflowState

Node = Callable[[WorkflowState], dict[str, object]]
SufficiencyEvaluator = Callable[[WorkflowState], bool]
QualityEvaluator = Callable[[ProposalBundle], bool]


def validate_topic_id(state: WorkflowState, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("topic ID 必须是字符串")
    known = {topic["topic_id"] for topic in state.get("topic_options", [])}
    if value not in known:
        raise ValueError(f"非法 topic ID：{value}")
    return value


@dataclass(slots=True)
class GraphDependencies:
    settings: LabSettings
    recorder: RunRecorder
    project_root: Path
    mode: Experiment02Mode = Experiment02Mode.FIXTURE
    sufficiency_evaluator: SufficiencyEvaluator | None = None
    quality_evaluator: QualityEvaluator | None = None
    fail_once_node: str | None = None
    failed_nodes: set[str] = field(default_factory=lambda: set[str]())

    def proposal_backend(self) -> ProposalBackend:
        if self.mode is Experiment02Mode.FIXTURE:
            return FixtureProposalBackend()
        method: StructuredOutputMethod = freeze_native_method(
            self.settings, project_root=self.project_root
        )
        return OpenAIProposalBackend(self.settings, method)


class WorkflowNodes:
    def __init__(self, dependencies: GraphDependencies) -> None:
        self.dependencies = dependencies

    def traced(self, name: str, node: Node) -> Node:
        def wrapped(state: WorkflowState) -> dict[str, object]:
            self.dependencies.recorder.record_event(
                "exp05.graph.node.started",
                {"node": name, "status": state.get("status")},
            )
            if (
                self.dependencies.fail_once_node == name
                and name not in self.dependencies.failed_nodes
            ):
                self.dependencies.failed_nodes.add(name)
                self.dependencies.recorder.record_event(
                    "exp05.graph.node.failed",
                    {"node": name, "reason": "injected_once"},
                )
                raise RuntimeError(f"injected one-shot failure: {name}")
            update = node(state)
            self.dependencies.recorder.record_event(
                "exp05.graph.node.finished",
                {"node": name, "update_keys": sorted(update)},
            )
            return update

        return wrapped

    def analyze_input(self, state: WorkflowState) -> dict[str, object]:
        return {
            "status": "input_analyzed",
            "input_question": state["input_question"].strip(),
        }

    def generate_topics(self, state: WorkflowState) -> dict[str, object]:
        del state
        return {
            "topic_options": [
                {
                    "topic_id": "topic-career-roadmap",
                    "title": "前端工程师的 AI 应用转型路线",
                    "rationale": "结合已有工程优势设计九十天验证计划",
                },
                {
                    "topic_id": "topic-agent-boundaries",
                    "title": "Agent 与固定流程的工程边界",
                    "rationale": "用成本、质量和可预测性比较自主决策",
                },
                {
                    "topic_id": "topic-rag-graph",
                    "title": "从 RAG 证据到可恢复内容工作流",
                    "rationale": "串联检索、人工选择和 checkpoint",
                },
            ],
            "status": "awaiting_topic_selection",
        }

    def wait_for_topic_selection(self, state: WorkflowState) -> dict[str, object]:
        # The interrupt is the first action; payload only reads checkpointed JSON state.
        selected = interrupt(
            {
                "kind": "topic_selection",
                "topic_ids": [topic["topic_id"] for topic in state["topic_options"]],
                "topics": state["topic_options"],
            }
        )
        topic_id = validate_topic_id(state, selected)
        title = next(
            topic["title"]
            for topic in state["topic_options"]
            if topic["topic_id"] == topic_id
        )
        return {
            "selected_topic_id": topic_id,
            "selected_topic_title": title,
            "status": "topic_selected",
        }

    def plan_research(self, state: WorkflowState) -> dict[str, object]:
        title = state["selected_topic_title"]
        return {
            "research_questions": [
                f"{title} 的核心实践路径是什么？",
                f"{title} 有哪些失败边界与硬约束？",
                f"{title} 应用什么指标评价价值？",
            ],
            "status": "research_planned",
        }

    def _web_pack(self) -> ResearchPack:
        fixture = load_fixture(self.dependencies.project_root)
        if self.dependencies.mode is Experiment02Mode.FIXTURE:
            tools = FixtureWebTools(fixture, self.dependencies.recorder.artifacts)
        else:
            tools = TavilyWebTools(
                self.dependencies.settings, self.dependencies.recorder.artifacts
            )
        return run_fixed_research(
            fixture.brief,
            tools=tools,
            budget=ExecutionBudget(),
            recorder=self.dependencies.recorder,
        )

    def _local_sources(self) -> list[SourceEvidence]:
        profile = load_embedding_profile(
            "minilm-multilingual-v1", self.dependencies.project_root
        )
        retrieval = RetrievalProfile(
            profile_id="exp05-fixed-rag-k2",
            chunk_size=800,
            overlap=120,
            top_k=2,
            profile_version="1",
        )
        documents = load_documents(self.dependencies.project_root)
        index, _ = RagIndex.rebuild(documents, retrieval, HashEmbeddings(profile))
        chunks: list[DocumentChunk] = []
        for case in load_retrieval_cases(self.dependencies.project_root):
            chunks.extend(index.retrieve_chunks(case.query, top_k=2))
        unique: dict[str, DocumentChunk] = {chunk.chunk_id: chunk for chunk in chunks}
        sources: list[SourceEvidence] = []
        known_ids: set[str] = set()
        for chunk in unique.values():
            artifact = self.dependencies.recorder.artifacts.put_text(
                chunk.content,
                category="local",
                media_type="text/markdown",
                metadata={
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.chunk_id,
                    "document_version": chunk.document_version,
                },
            )
            source_id = f"src-{chunk.content_hash[:12]}"
            if source_id in known_ids:
                continue
            known_ids.add(source_id)
            sources.append(
                SourceEvidence(
                    source_id=source_id,
                    title=chunk.title,
                    url=f"https://local.invalid/{chunk.document_id}/{chunk.chunk_id}",
                    artifact=artifact,
                    excerpt=chunk.content[:500],
                )
            )
        return sources

    def collect_evidence(self, state: WorkflowState) -> dict[str, object]:
        web = self._web_pack()
        local_sources = self._local_sources()
        sources_by_id = {source.source_id: source for source in web.sources}
        sources_by_id.update({source.source_id: source for source in local_sources})
        sources = list(sources_by_id.values())
        findings = [
            ResearchFinding(
                claim=f"{source.title}：{source.excerpt[:220]}",
                source_ids=[source.source_id],
            )
            for source in sources
        ]
        pack = ResearchPack(
            brief=web.brief,
            queries=[*web.queries, *state["research_questions"]],
            sources=sources,
            findings=findings,
            tool_errors=web.tool_errors,
        )
        return {
            "research_round": state.get("research_round", 0) + 1,
            "source_evidence": [
                cast(dict[str, object], source.model_dump(mode="json")) for source in sources
            ],
            "artifact_refs": [
                {
                    "run_id": self.dependencies.recorder.run_id,
                    **cast(dict[str, object], source.artifact.model_dump(mode="json")),
                }
                for source in sources
            ],
            "research_pack": cast(dict[str, object], pack.model_dump(mode="json")),
            "status": "evidence_collected",
        }

    def assess_evidence(self, state: WorkflowState) -> dict[str, object]:
        evaluator = self.dependencies.sufficiency_evaluator
        sufficient = evaluator(state) if evaluator else len(state["source_evidence"]) >= 3
        at_limit = state["research_round"] >= 2
        return {
            "status": "evidence_sufficient" if sufficient else "evidence_insufficient",
            "evidence_warning": bool(not sufficient and at_limit),
        }

    def finalize(self, state: WorkflowState) -> dict[str, object]:
        pack = ResearchPack.model_validate(state["research_pack"])
        if state.get("evidence_warning"):
            pack.tool_errors.append(
                {
                    "code": "insufficient_evidence_after_max_rounds",
                    "message": "两轮研究后仍未通过充分性门禁",
                    "retryable": False,
                }
            )
        proposal = finalize_proposal(
            pack,
            backend=self.dependencies.proposal_backend(),
            budget=ExecutionBudget(),
            recorder=self.dependencies.recorder,
        )
        return {
            "research_pack": cast(dict[str, object], pack.model_dump(mode="json")),
            "proposal": cast(dict[str, object], proposal.model_dump(mode="json")),
            "status": "proposal_generated",
        }

    def quality_check(self, state: WorkflowState) -> dict[str, object]:
        proposal = ProposalBundle.model_validate(state["proposal"])
        evaluator = self.dependencies.quality_evaluator
        passed = evaluator(proposal) if evaluator else len(proposal.recommendations) >= 2
        return {
            "quality_result": {
                "passed": passed,
                "rubric": "citations-actionability-structure-v1",
                "score": 5 if passed else 2,
            },
            "status": "quality_passed" if passed else "quality_failed",
        }

    def revise(self, state: WorkflowState) -> dict[str, object]:
        pack = ResearchPack.model_validate(state["research_pack"])
        existing = ProposalBundle.model_validate(state["proposal"])
        count = state.get("revision_count", 0) + 1
        draft = ProposalDraft(
            title=existing.title,
            summary=f"{existing.summary}（已完成第 {count} 轮受限修订。）",
            recommendations=existing.recommendations,
        )
        revised = ProposalBundle(
            **draft.model_dump(mode="python"),
            markdown=render_proposal_markdown(draft, pack),
        )
        return {
            "proposal": cast(dict[str, object], revised.model_dump(mode="json")),
            "revision_count": count,
            "status": "proposal_revised",
        }

    def persist(self, state: WorkflowState) -> dict[str, object]:
        proposal = ProposalBundle.model_validate(state["proposal"])
        quality = state.get("quality_result", {})
        passed = bool(quality.get("passed"))
        final_status = "succeeded" if passed else "needs_review"
        persisted_state = {**dict(state), "status": final_status}
        self.dependencies.recorder.write_json("workflow-state.json", persisted_state)
        self.dependencies.recorder.write_json("proposal.json", proposal)
        self.dependencies.recorder.write_text("proposal.md", proposal.markdown)
        return {"status": final_status}


def build_workflow(dependencies: GraphDependencies, checkpointer: Any) -> Any:
    nodes = WorkflowNodes(dependencies)
    builder: Any = StateGraph(WorkflowState)
    builder.add_node("analyze_input", nodes.traced("analyze_input", nodes.analyze_input))
    builder.add_node("generate_topics", nodes.traced("generate_topics", nodes.generate_topics))
    # The wait node is not traced because nothing may run before interrupt.
    builder.add_node("wait_for_topic_selection", nodes.wait_for_topic_selection)
    builder.add_node("plan_research", nodes.traced("plan_research", nodes.plan_research))
    builder.add_node(
        "collect_evidence", nodes.traced("collect_evidence", nodes.collect_evidence)
    )
    builder.add_node(
        "assess_evidence", nodes.traced("assess_evidence", nodes.assess_evidence)
    )
    builder.add_node("finalize_proposal", nodes.traced("finalize_proposal", nodes.finalize))
    builder.add_node("quality_check", nodes.traced("quality_check", nodes.quality_check))
    builder.add_node("revise_proposal", nodes.traced("revise_proposal", nodes.revise))
    builder.add_node("persist_artifacts", nodes.traced("persist_artifacts", nodes.persist))

    builder.add_edge(START, "analyze_input")
    builder.add_edge("analyze_input", "generate_topics")
    builder.add_edge("generate_topics", "wait_for_topic_selection")
    builder.add_edge("wait_for_topic_selection", "plan_research")
    builder.add_edge("plan_research", "collect_evidence")
    builder.add_edge("collect_evidence", "assess_evidence")

    def route_evidence(state: WorkflowState) -> str:
        if state["status"] == "evidence_sufficient" or state["research_round"] >= 2:
            target = "finalize_proposal"
        else:
            target = "collect_evidence"
        dependencies.recorder.record_event(
            "exp05.graph.route",
            {
                "route": "evidence",
                "target": target,
                "research_round": state["research_round"],
            },
        )
        return target

    builder.add_conditional_edges(
        "assess_evidence",
        route_evidence,
        {
            "collect_evidence": "collect_evidence",
            "finalize_proposal": "finalize_proposal",
        },
    )
    builder.add_edge("finalize_proposal", "quality_check")

    def route_quality(state: WorkflowState) -> str:
        result = state.get("quality_result", {})
        passed = bool(result.get("passed"))
        target = (
            "persist_artifacts"
            if passed or state["revision_count"] >= 2
            else "revise_proposal"
        )
        dependencies.recorder.record_event(
            "exp05.graph.route",
            {
                "route": "quality",
                "target": target,
                "revision_count": state["revision_count"],
            },
        )
        return target

    builder.add_conditional_edges(
        "quality_check",
        route_quality,
        {
            "revise_proposal": "revise_proposal",
            "persist_artifacts": "persist_artifacts",
        },
    )
    builder.add_edge("revise_proposal", "quality_check")
    builder.add_edge("persist_artifacts", END)
    return builder.compile(checkpointer=checkpointer, name="exp05_content_workflow")
