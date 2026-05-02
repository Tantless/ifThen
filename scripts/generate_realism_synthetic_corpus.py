from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "tests" / "fixtures" / "realism_synthetic"
DEFAULT_ENV_FILE = ROOT / "llm_match_config.env"
EXPORT_TIME = "2026-05-02 20:00:00"
SELF_NAME = "我"


@dataclass(frozen=True, slots=True)
class AnchorMessage:
    speaker: str
    content: str


@dataclass(frozen=True, slots=True)
class ChunkPlan:
    label: str
    start_at: str
    end_at: str
    target_count: int
    relationship_state: str
    required_beats: list[str]
    anchors: list[AnchorMessage] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RewritePoint:
    id: str
    cutoff: str
    speaker: str
    original: str
    suggested_rewrite: str
    cutoff_only_read: str
    modeler_only_read: str


@dataclass(frozen=True, slots=True)
class TruthFact:
    id: str
    revealed_after: str
    fact: str
    evidence_anchor: AnchorMessage
    use_policy: str


@dataclass(frozen=True, slots=True)
class CasePlan:
    slug: str
    title: str
    other_name: str
    date_range: tuple[str, str]
    premise: str
    self_style: str
    other_style: str
    hidden_state: str
    reviewer_focus: str
    chunks: list[ChunkPlan]
    rewrite_points: list[RewritePoint]
    truth_facts: list[TruthFact]


@dataclass(slots=True)
class GeneratedMessage:
    speaker: str
    content: str
    timestamp: str = ""


class LLMGenerationError(RuntimeError):
    pass


class ResponsesJsonClient:
    def __init__(self, *, base_url: str, api_key: str, model: str, timeout_seconds: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def request_json(
        self,
        *,
        instructions: str,
        prompt: str,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        content = self._post_responses(
            instructions=instructions,
            prompt=prompt,
            max_output_tokens=max_output_tokens,
        )
        return _parse_json_object(content)

    def _post_responses(self, *, instructions: str, prompt: str, max_output_tokens: int) -> str:
        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": prompt,
            "text": {"format": {"type": "json_object"}},
            "max_output_tokens": max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        last_error: str | None = None
        for attempt in range(1, 4):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(f"{self.base_url}/responses", headers=headers, json=payload)
            except httpx.HTTPError as exc:
                last_error = f"Responses request failed: {type(exc).__name__}: {exc}"
                if attempt < 3:
                    time.sleep(2 * attempt)
                    continue
                raise LLMGenerationError(last_error) from exc

            if response.status_code < 400:
                break
            last_error = f"Responses request failed with status {response.status_code}: {response.text[:400]}"
            if response.status_code in {408, 409, 429, 500, 502, 503, 504, 524} and attempt < 3:
                time.sleep(2 * attempt)
                continue
            raise LLMGenerationError(last_error)
        else:
            raise LLMGenerationError(last_error or "Responses request failed")

        data = response.json()
        if data.get("status") not in {None, "completed"}:
            raise LLMGenerationError(f"Responses request did not complete: {data.get('status')}")

        for item in data.get("output") or []:
            if item.get("type") != "message":
                continue
            for content_item in item.get("content") or []:
                if content_item.get("type") == "output_text" and isinstance(content_item.get("text"), str):
                    return content_item["text"]
        raise LLMGenerationError("Responses output did not contain output_text")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic realism QQChatExporter fixtures.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--case", choices=[case.slug for case in build_case_plans()], action="append")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--no-review", action="store_true")
    args = parser.parse_args()

    config = load_env_file(args.env_file)
    client = ResponsesJsonClient(
        base_url=config["API_URL"],
        api_key=config["API_KEY"],
        model=config["MODEL_NAME"],
    )

    selected_slugs = set(args.case or [])
    for case_plan in build_case_plans():
        if selected_slugs and case_plan.slug not in selected_slugs:
            continue
        case_dir = args.output_dir / case_plan.slug
        conversation_path = case_dir / "conversation.txt"
        if args.skip_existing and conversation_path.exists():
            print(f"skip existing {case_plan.slug}")
            continue
        generate_case(
            client=client,
            case_plan=case_plan,
            case_dir=case_dir,
            run_review=not args.no_review,
        )
    return 0


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise LLMGenerationError(f"env file does not exist: {path}")
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    missing = [key for key in ("API_URL", "API_KEY", "MODEL_NAME") if not values.get(key)]
    if missing:
        raise LLMGenerationError(f"env file missing required keys: {', '.join(missing)}")
    return values


def generate_case(
    *,
    client: ResponsesJsonClient,
    case_plan: CasePlan,
    case_dir: Path,
    run_review: bool,
) -> None:
    print(f"generating {case_plan.slug}: {case_plan.title}")
    case_dir.mkdir(parents=True, exist_ok=True)
    all_messages: list[GeneratedMessage] = []
    continuity_summary = "尚未开始。"

    for index, chunk in enumerate(case_plan.chunks, start=1):
        print(f"  chunk {index:02d}/{len(case_plan.chunks)} {chunk.label}")
        chunk_messages, continuity_summary = generate_chunk_with_retries(
            client=client,
            case_plan=case_plan,
            chunk=chunk,
            continuity_summary=continuity_summary,
        )
        assign_timestamps(
            messages=chunk_messages,
            start_at=chunk.start_at,
            end_at=chunk.end_at,
            seed=f"{case_plan.slug}-{index}",
        )
        normalize_time_words(chunk_messages)
        all_messages.extend(chunk_messages)
        time.sleep(0.5)

    write_case_files(
        case_plan=case_plan,
        case_dir=case_dir,
        messages=all_messages,
        review_payload=None,
    )

    review_payload = None
    if run_review:
        print(f"  reviewing {case_plan.slug}")
        review_payload = review_case(client=client, case_plan=case_plan, case_dir=case_dir, messages=all_messages)
        write_case_files(
            case_plan=case_plan,
            case_dir=case_dir,
            messages=all_messages,
            review_payload=review_payload,
        )
        if not review_payload.get("pass", False):
            raise LLMGenerationError(f"review failed for {case_plan.slug}: {review_payload}")

    print(f"  done {case_plan.slug}: {len(all_messages)} messages")


def generate_chunk_with_retries(
    *,
    client: ResponsesJsonClient,
    case_plan: CasePlan,
    chunk: ChunkPlan,
    continuity_summary: str,
) -> tuple[list[GeneratedMessage], str]:
    validation_error = ""
    for attempt in range(1, 4):
        payload = client.request_json(
            instructions=build_chunk_instructions(case_plan),
            prompt=build_chunk_prompt(
                case_plan=case_plan,
                chunk=chunk,
                continuity_summary=continuity_summary,
                validation_error=validation_error,
            ),
            max_output_tokens=9000,
        )
        try:
            messages = parse_chunk_payload(payload=payload, case_plan=case_plan, chunk=chunk)
            summary = str(payload.get("continuity_summary", "")).strip()
            if not summary:
                summary = build_fallback_continuity_summary(messages)
            return messages, summary
        except LLMGenerationError as exc:
            validation_error = f"第 {attempt} 次输出未通过校验：{exc}"
            print(f"    retry: {validation_error}")
            time.sleep(1.0)
    raise LLMGenerationError(f"chunk failed after retries: {case_plan.slug} {chunk.label}")


def build_chunk_instructions(case_plan: CasePlan) -> str:
    return (
        "你是中文聊天记录生成器，只输出 JSON。"
        "你的目标是生成高度拟真的合成私聊消息，用于反事实聊天评估。"
        "不要写小说旁白，不要解释，不要输出 Markdown。"
        "所有人物、地点、组织都必须是虚构或泛称，禁止真实姓名、真实学校、真实公司、真实联系方式。"
        f"固定说话人只有两个：`{SELF_NAME}` 和 `{case_plan.other_name}`。"
    )


def build_chunk_prompt(
    *,
    case_plan: CasePlan,
    chunk: ChunkPlan,
    continuity_summary: str,
    validation_error: str,
) -> str:
    anchor_lines = [
        {"speaker": anchor.speaker, "content": anchor.content}
        for anchor in chunk.anchors
    ]
    prompt = {
        "format_instruction": "Return only one json object. Do not include markdown or extra text.",
        "output_schema": {
            "messages": [
                {
                    "speaker": f"只能是 {SELF_NAME} 或 {case_plan.other_name}",
                    "content": "单行中文聊天内容，不含换行",
                }
            ],
            "continuity_summary": "120 字以内，概括本 chunk 结束后的关系状态和未解决信息",
            "quality_notes": ["简短列出你如何保持拟真性"],
        },
        "hard_requirements": [
            f"messages 目标为 {chunk.target_count} 条，合理范围 {chunk.target_count} 到 {chunk.target_count + 20} 条；不能少于 {chunk.target_count} 条。",
            "每条 content 必须像即时聊天：大多数 2-24 个汉字，少数严肃消息可以 25-70 个汉字。",
            "允许连续同一人发多条、撤回式补充、话题跳跃、短回复、语气词、轻微重复。",
            "不要让双方机械轮流，不要每条都完整标点，不要写成文学对白。",
            "禁止电话、邮箱、链接、微信号、QQ 号、身份证、真实学校/公司/地址。",
            "禁止出现 `时间:`、`内容:`、说话人标签或消息序号。",
            "锚点消息必须逐字出现一次，不要改字，不要拆分。",
        ],
        "case": {
            "title": case_plan.title,
            "premise": case_plan.premise,
            "self_style": case_plan.self_style,
            "other_style": case_plan.other_style,
            "hidden_state": case_plan.hidden_state,
        },
        "chunk": {
            "label": chunk.label,
            "time_range": f"{chunk.start_at} - {chunk.end_at}",
            "relationship_state": chunk.relationship_state,
            "required_beats": chunk.required_beats,
            "anchor_messages": anchor_lines,
        },
        "continuity_before_chunk": continuity_summary,
    }
    if validation_error:
        prompt["previous_validation_error"] = validation_error
    return json.dumps(prompt, ensure_ascii=False, indent=2)


def parse_chunk_payload(*, payload: dict[str, Any], case_plan: CasePlan, chunk: ChunkPlan) -> list[GeneratedMessage]:
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        raise LLMGenerationError("messages is not a list")
    if len(raw_messages) < chunk.target_count:
        raise LLMGenerationError(f"messages count {len(raw_messages)} < {chunk.target_count}")

    messages: list[GeneratedMessage] = []
    for index, item in enumerate(raw_messages, start=1):
        if not isinstance(item, dict):
            raise LLMGenerationError(f"message {index} is not an object")
        speaker = str(item.get("speaker", "")).strip()
        content = sanitize_content(str(item.get("content", "")))
        if speaker not in {SELF_NAME, case_plan.other_name}:
            raise LLMGenerationError(f"message {index} has invalid speaker: {speaker}")
        validate_content(content=content, index=index)
        messages.append(GeneratedMessage(speaker=speaker, content=content))

    missing_anchors = [
        f"{anchor.speaker}: {anchor.content}"
        for anchor in chunk.anchors
        if not any(message.speaker == anchor.speaker and message.content == anchor.content for message in messages)
    ]
    if missing_anchors:
        raise LLMGenerationError("missing anchor messages: " + " | ".join(missing_anchors))

    return messages


def sanitize_content(content: str) -> str:
    content = re.sub(r"\s+", " ", content.replace("\n", " ")).strip()
    for prefix in ("内容:", "内容：", "我:", "我："):
        if content.startswith(prefix):
            content = content[len(prefix) :].strip()
    return content


def validate_content(*, content: str, index: int) -> None:
    if not content:
        raise LLMGenerationError(f"message {index} has empty content")
    if len(content) > 90:
        raise LLMGenerationError(f"message {index} too long: {len(content)}")
    forbidden_patterns = [
        r"\d{6,}",
        r"https?://",
        r"www\.",
        r"@[A-Za-z0-9_]+",
        r"微信号",
        r"QQ号",
        r"手机号",
        r"身份证",
        r"清华|北大|复旦|上交|腾讯|阿里|字节|美团",
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, content, flags=re.IGNORECASE):
            raise LLMGenerationError(f"message {index} contains forbidden pattern: {pattern}")


def assign_timestamps(*, messages: list[GeneratedMessage], start_at: str, end_at: str, seed: str) -> None:
    start = datetime.strptime(start_at, "%Y-%m-%d %H:%M:%S")
    end = datetime.strptime(end_at, "%Y-%m-%d %H:%M:%S")
    if end <= start:
        raise LLMGenerationError(f"invalid time range: {start_at} - {end_at}")

    rng = random.Random(seed)
    session_count = min(max(5, len(messages) // 16), 10)
    sizes = split_count(len(messages), session_count, rng)
    bases: list[datetime] = []
    day_count = max(1, (end.date() - start.date()).days + 1)
    for index in range(session_count):
        day_offset = min(
            day_count - 1,
            max(0, round((index + rng.random() * 0.7) * (day_count - 1) / max(1, session_count - 1))),
        )
        session_date = start.date() + timedelta(days=day_offset)
        hour = weighted_chat_hour(rng)
        base = datetime.combine(session_date, datetime.min.time()).replace(
            hour=hour,
            minute=rng.randint(0, 55),
            second=rng.randint(0, 50),
        )
        if base < start:
            base = start + timedelta(minutes=rng.randint(3, 90))
        if base > end:
            base = end - timedelta(minutes=rng.randint(10, 120))
        bases.append(base)
    bases.sort()

    cursor = start
    message_index = 0
    for session_index, size in enumerate(sizes):
        cursor = max(cursor + timedelta(seconds=rng.randint(30, 600)), bases[session_index])
        for _ in range(size):
            if message_index >= len(messages):
                break
            cursor += timedelta(seconds=rng.randint(3, 210))
            if cursor >= end:
                cursor = end - timedelta(seconds=len(messages) - message_index)
            messages[message_index].timestamp = cursor.strftime("%Y-%m-%d %H:%M:%S")
            message_index += 1

    for index in range(1, len(messages)):
        if messages[index].timestamp <= messages[index - 1].timestamp:
            previous = datetime.strptime(messages[index - 1].timestamp, "%Y-%m-%d %H:%M:%S")
            messages[index].timestamp = (previous + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")


def weighted_chat_hour(rng: random.Random) -> int:
    hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
    weights = [3, 3, 4, 3, 5, 3, 3, 4, 4, 5, 7, 9, 11, 12, 10, 5]
    return rng.choices(hours, weights=weights, k=1)[0]


def normalize_time_words(messages: list[GeneratedMessage]) -> None:
    for message in messages:
        hour = int(message.timestamp[11:13])
        content = message.content
        if hour >= 14:
            content = re.sub(r"^(早呀|早啊|早安|早)$", "在吗", content)
            content = content.replace("早饭", "吃的")
            content = content.replace("早上", "刚才")
        if hour >= 15:
            content = content.replace("中午吃", "刚才吃")
            content = content.replace("中午", "刚才")
        if hour < 18:
            content = content.replace("晚安", "先不聊啦")
        if hour < 11:
            content = content.replace("宵夜", "吃的")
        message.content = content


def split_count(total: int, parts: int, rng: random.Random) -> list[int]:
    weights = [rng.uniform(0.6, 1.7) for _ in range(parts)]
    raw_sizes = [max(1, int(total * weight / sum(weights))) for weight in weights]
    while sum(raw_sizes) < total:
        raw_sizes[rng.randrange(parts)] += 1
    while sum(raw_sizes) > total:
        index = rng.randrange(parts)
        if raw_sizes[index] > 1:
            raw_sizes[index] -= 1
    return raw_sizes


def write_case_files(
    *,
    case_plan: CasePlan,
    case_dir: Path,
    messages: list[GeneratedMessage],
    review_payload: dict[str, Any] | None,
) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "conversation.txt").write_text(
        render_conversation(case_plan=case_plan, messages=messages),
        encoding="utf-8",
        newline="\n",
    )
    (case_dir / "timeline.md").write_text(render_timeline(case_plan), encoding="utf-8", newline="\n")
    (case_dir / "rewrite-points.md").write_text(
        render_rewrite_points(case_plan=case_plan, messages=messages),
        encoding="utf-8",
        newline="\n",
    )
    (case_dir / "truth-after-cutoff.md").write_text(
        render_truth_facts(case_plan=case_plan, messages=messages),
        encoding="utf-8",
        newline="\n",
    )
    (case_dir / "generation-notes.md").write_text(
        render_generation_notes(case_plan=case_plan, messages=messages, review_payload=review_payload),
        encoding="utf-8",
        newline="\n",
    )


def render_conversation(*, case_plan: CasePlan, messages: list[GeneratedMessage]) -> str:
    lines = [
        "[QQChatExporter V5 / https://github.com/shuakami/qq-chat-exporter]",
        "",
        f"聊天名称: {case_plan.other_name}",
        "聊天类型: 私聊",
        f"导出时间: {EXPORT_TIME}",
        f"消息总数: {len(messages)}",
        f"时间范围: {messages[0].timestamp} - {messages[-1].timestamp}",
        "",
        "",
    ]
    for message in messages:
        lines.extend(
            [
                f"{message.speaker}:",
                f"时间: {message.timestamp}",
                f"内容: {message.content}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_timeline(case_plan: CasePlan) -> str:
    lines = [
        f"# {case_plan.title}",
        "",
        "## 关系设定",
        "",
        f"- 我方表达风格：{case_plan.self_style}",
        f"- 对方表达风格：{case_plan.other_style}",
        f"- 隐含状态：{case_plan.hidden_state}",
        "",
        "## 时间线",
        "",
    ]
    for chunk in case_plan.chunks:
        lines.extend(
            [
                f"### {chunk.label}",
                "",
                f"- 时间：{chunk.start_at} - {chunk.end_at}",
                f"- 关系状态：{chunk.relationship_state}",
                "- 关键节点：",
            ]
        )
        lines.extend([f"  - {beat}" for beat in chunk.required_beats])
        if chunk.anchors:
            lines.append("- 锚点消息：")
            lines.extend([f"  - `{anchor.speaker}`：{anchor.content}" for anchor in chunk.anchors])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_rewrite_points(*, case_plan: CasePlan, messages: list[GeneratedMessage]) -> str:
    lines = [f"# {case_plan.title}：关键改写点", ""]
    for point in case_plan.rewrite_points:
        actual_cutoff = find_message_timestamp(messages, speaker=point.speaker, content=point.original) or point.cutoff
        lines.extend(
            [
                f"## {point.id}",
                "",
                f"- cutoff：{actual_cutoff}",
                f"- 原说话人：`{point.speaker}`",
                f"- 原句：{point.original}",
                f"- 建议改写：{point.suggested_rewrite}",
                f"- cutoff-only 评估：{point.cutoff_only_read}",
                f"- modeler-only evidence 评估：{point.modeler_only_read}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_truth_facts(*, case_plan: CasePlan, messages: list[GeneratedMessage]) -> str:
    lines = [f"# {case_plan.title}：cutoff 后真相", ""]
    for fact in case_plan.truth_facts:
        actual_reveal = (
            find_message_timestamp(
                messages,
                speaker=fact.evidence_anchor.speaker,
                content=fact.evidence_anchor.content,
            )
            or fact.revealed_after
        )
        lines.extend(
            [
                f"## {fact.id}",
                "",
                f"- 揭示时间：{actual_reveal}",
                f"- 客观事实：{fact.fact}",
                f"- 证据锚点：`{fact.evidence_anchor.speaker}`：{fact.evidence_anchor.content}",
                f"- 使用策略：{fact.use_policy}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def find_message_timestamp(messages: list[GeneratedMessage], *, speaker: str, content: str) -> str | None:
    for message in messages:
        if message.speaker == speaker and message.content == content:
            return message.timestamp
    return None


def render_generation_notes(
    *,
    case_plan: CasePlan,
    messages: list[GeneratedMessage],
    review_payload: dict[str, Any] | None,
) -> str:
    lines = [
        f"# {case_plan.title}：生成记录",
        "",
        "## 生成约束",
        "",
        "- 通过 `scripts/generate_realism_synthetic_corpus.py` 调用本地 `llm_match_config.env` 中的 Responses API 配置生成。",
        "- API key 只在本地读取，未写入本文件或语料。",
        "- LLM 输出 JSON 消息数组，脚本统一写成 QQChatExporter 兼容文本。",
        "- 脚本校验消息数量、说话人、锚点消息、单行内容和隐私风险词。",
        "",
        "## 数量与跨度",
        "",
        f"- 消息数：{len(messages)}",
        f"- 时间范围：{messages[0].timestamp} - {messages[-1].timestamp}",
        f"- chunk 数：{len(case_plan.chunks)}",
        "",
        "## prompt 结构",
        "",
        "- system/instructions：限定为中文合成私聊消息生成器，只输出 JSON，固定双方说话人，禁止真实 PII。",
        "- user/input：提供关系设定、上一 chunk 连续性摘要、当前 chunk 时间范围、关系状态、必含事件和逐字锚点消息。",
        "- output：`messages`、`continuity_summary`、`quality_notes`。",
        "",
        "## 自动复核",
        "",
    ]
    if review_payload is None:
        lines.append("- 尚未运行自动复核。")
    else:
        lines.extend(
            [
                f"- 拟真性评分：{review_payload.get('realism_score')}",
                f"- 故事一致性评分：{review_payload.get('story_alignment_score')}",
                f"- 项目标准评分：{review_payload.get('project_standard_score')}",
                f"- 是否通过：{review_payload.get('pass')}",
                f"- 复核摘要：{review_payload.get('review_summary')}",
                "- 缺陷记录：",
            ]
        )
        defects = review_payload.get("defects") or []
        if defects:
            lines.extend([f"  - {defect}" for defect in defects])
        else:
            lines.append("  - 未发现阻断问题。")
    return "\n".join(lines).rstrip() + "\n"


def review_case(
    *,
    client: ResponsesJsonClient,
    case_plan: CasePlan,
    case_dir: Path,
    messages: list[GeneratedMessage],
) -> dict[str, Any]:
    sample = build_review_sample(case_plan=case_plan, messages=messages)
    payload = client.request_json(
        instructions=(
            "你是合成聊天记录质量审查员，只输出 JSON。"
            "请严格审查拟真性、故事一致性、项目可用性和隐私风险。"
        ),
        prompt=json.dumps(
            {
                "format_instruction": "Return only one json object. Do not include markdown or extra text.",
                "output_schema": {
                    "realism_score": "1-5",
                    "story_alignment_score": "1-5",
                    "project_standard_score": "1-5",
                    "pass": "bool",
                    "defects": ["阻断问题列表，没有则空数组"],
                    "review_summary": "120 字以内中文总结",
                },
                "acceptance": [
                    "聊天必须像真实日常私聊，不应像剧情梗概。",
                    "故事不能偏离 case premise。",
                    "锚点消息要能支撑关键改写点和 cutoff 后真相。",
                    "不能包含真实姓名、学校、公司、联系方式或链接。",
                    "必须服务产品亮点：只看 cutoff 前容易误判，cutoff 后客观事实能让评估更保守。",
                ],
                "case": {
                    "title": case_plan.title,
                    "premise": case_plan.premise,
                    "reviewer_focus": case_plan.reviewer_focus,
                    "rewrite_points": [
                        {
                            "id": point.id,
                            "cutoff": find_message_timestamp(messages, speaker=point.speaker, content=point.original)
                            or point.cutoff,
                            "speaker": point.speaker,
                            "original": point.original,
                            "suggested_rewrite": point.suggested_rewrite,
                            "cutoff_only_read": point.cutoff_only_read,
                            "modeler_only_read": point.modeler_only_read,
                        }
                        for point in case_plan.rewrite_points
                    ],
                    "truth_facts": [
                        {
                            "id": fact.id,
                            "revealed_after": find_message_timestamp(
                                messages,
                                speaker=fact.evidence_anchor.speaker,
                                content=fact.evidence_anchor.content,
                            )
                            or fact.revealed_after,
                            "fact": fact.fact,
                            "evidence_anchor": {
                                "speaker": fact.evidence_anchor.speaker,
                                "content": fact.evidence_anchor.content,
                            },
                        }
                        for fact in case_plan.truth_facts
                    ],
                },
                "conversation_sample": sample,
                "conversation_path": str(case_dir / "conversation.txt"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        max_output_tokens=4000,
    )
    return normalize_review_payload(payload)


def build_review_sample(*, case_plan: CasePlan, messages: list[GeneratedMessage]) -> list[dict[str, str]]:
    target_indices: set[int] = set(range(0, min(30, len(messages))))
    target_indices.update(range(max(0, len(messages) - 30), len(messages)))
    anchor_contents = {point.original for point in case_plan.rewrite_points}
    anchor_contents.update(fact.evidence_anchor.content for fact in case_plan.truth_facts)
    for index, message in enumerate(messages):
        if message.content in anchor_contents:
            target_indices.update(range(max(0, index - 12), min(len(messages), index + 13)))
    step = max(1, len(messages) // 20)
    target_indices.update(range(0, len(messages), step))
    return [
        {
            "seq": str(index + 1),
            "timestamp": messages[index].timestamp,
            "speaker": messages[index].speaker,
            "content": messages[index].content,
        }
        for index in sorted(target_indices)
    ]


def normalize_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    def score(name: str) -> int:
        value = payload.get(name, 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    review = {
        "realism_score": score("realism_score"),
        "story_alignment_score": score("story_alignment_score"),
        "project_standard_score": score("project_standard_score"),
        "pass": bool(payload.get("pass")),
        "defects": payload.get("defects") if isinstance(payload.get("defects"), list) else [],
        "review_summary": str(payload.get("review_summary", "")).strip(),
    }
    if min(review["realism_score"], review["story_alignment_score"], review["project_standard_score"]) < 4:
        review["pass"] = False
    return review


def build_fallback_continuity_summary(messages: list[GeneratedMessage]) -> str:
    tail = " / ".join(f"{message.speaker}:{message.content}" for message in messages[-6:])
    return f"本段结束时最近互动为：{tail}"


def _parse_json_object(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise LLMGenerationError("LLM response did not contain a JSON object")
        payload = json.loads(stripped[start : end + 1])
    if not isinstance(payload, dict):
        raise LLMGenerationError("LLM JSON response must be an object")
    return payload


def build_case_plans() -> list[CasePlan]:
    return [
        build_hidden_trauma_case(),
        build_conflict_repair_case(),
        build_missed_window_case(),
    ]


def build_hidden_trauma_case() -> CasePlan:
    other = "小禾"
    return CasePlan(
        slug="case-01-hidden-trauma-confession",
        title="隐藏心理阴影导致告白失败",
        other_name=other,
        date_range=("2026-02-03 10:10:00", "2026-05-05 22:30:00"),
        premise="双方二月偶然相识后开始私聊，三四月逐渐暧昧；我方以为告白只差临门一脚，但对方因过往关系阴影害怕进入确定关系，告白后才解释真实顾虑。",
        self_style="回应积极，喜欢接梗和轻微推进，越到后期越容易把暧昧理解为确定信号。",
        other_style="细腻、慢热、会主动分享日常，但遇到关系定义会绕开、开玩笑或突然变短。",
        hidden_state="对方在 cutoff 前没有明说心理阴影，只留下别对我太好、我有点怕认真这类弱信号。",
        reviewer_focus="cutoff 前看似暧昧充足，cutoff 后真相说明更好说辞也不必然成功。",
        chunks=[
            ChunkPlan(
                "02月初：偶然相识后迁移到日常聊天",
                "2026-02-03 10:10:00",
                "2026-02-08 23:20:00",
                90,
                "刚加上好友，礼貌但有好奇心。",
                ["从活动现场/书店附近的偶遇聊起。", "互相确认共同兴趣：旧书、独立音乐、散步。", "出现第一次轻松玩笑，但不暧昧。"],
            ),
            ChunkPlan(
                "02月中：共同兴趣与碎片陪伴",
                "2026-02-09 08:30:00",
                "2026-02-16 23:40:00",
                90,
                "日常频率上升，开始互相报备小事。",
                ["聊歌单、咖啡和下雨天。", "对方会在晚间主动分享照片感受但不发真实图片。", "我方开始习惯性等她消息。"],
            ),
            ChunkPlan(
                "02月下：轻微暧昧出现",
                "2026-02-17 09:10:00",
                "2026-02-25 23:50:00",
                90,
                "关系变轻松，互相调侃开始带一点专属感。",
                ["出现早安/晚安式收尾。", "对方说跟我聊天比刷短视频安心。", "我方开始试探周末见面。"],
            ),
            ChunkPlan(
                "03月初：线下见面后升温",
                "2026-02-26 10:00:00",
                "2026-03-05 23:40:00",
                90,
                "第一次短暂线下见面后，聊天密度继续上升。",
                ["一起走过一段路，聊到小吃和旧电影。", "对方记住我方偏好。", "我方开始明显更主动。"],
            ),
            ChunkPlan(
                "03月中：靠近与退缩并存",
                "2026-03-06 08:20:00",
                "2026-03-16 23:50:00",
                90,
                "暧昧增强，但对方开始在被认真对待时闪避。",
                ["对方说自己慢热。", "我方说出偏占有的玩笑。", "对方没有爆发，只是短暂沉默后转移话题。"],
                anchors=[AnchorMessage(SELF_NAME, "那你以后就归我管了？")],
            ),
            ChunkPlan(
                "03月下：暧昧证据继续累积",
                "2026-03-17 09:00:00",
                "2026-03-27 23:55:00",
                90,
                "我方越来越乐观，对方仍用轻松表达维持距离。",
                ["聊到演出、晚饭和下班后的疲惫。", "对方偶尔说别对我太好。", "我方把这些理解成害羞。"],
                anchors=[AnchorMessage(other, "你别对我太好，我会有负担的")],
            ),
            ChunkPlan(
                "04月初：明显亲近但不定义",
                "2026-03-28 10:30:00",
                "2026-04-07 23:45:00",
                90,
                "双方像准情侣一样聊天，但没有关系确认。",
                ["对方主动问我方行程。", "我方提到以后一起做很多事。", "对方回应温柔但避开确定承诺。"],
            ),
            ChunkPlan(
                "04月中：我方开始催促确定性",
                "2026-04-08 08:30:00",
                "2026-04-16 23:50:00",
                90,
                "暧昧强，我方开始不满足于模糊状态。",
                ["对方多次用忙、困、先不想这些理由岔开。", "我方把回避理解成撒娇或害羞。", "出现第二个关键可改写点。"],
                anchors=[AnchorMessage(SELF_NAME, "你别总逃，我都这么明显了")],
            ),
            ChunkPlan(
                "04月下旬前：告白前的过度乐观",
                "2026-04-17 09:20:00",
                "2026-04-21 23:40:00",
                90,
                "我方判断时机成熟，对方焦虑但没讲原因。",
                ["对方反复确认我方是不是很认真。", "我方准备告白。", "对方说自己有点怕，但没有展开。"],
                anchors=[AnchorMessage(other, "我有点怕你太认真")],
            ),
            ChunkPlan(
                "04月22日：告白失败",
                "2026-04-22 09:10:00",
                "2026-04-22 23:30:00",
                90,
                "告白发生，对方犹豫拒绝，关系温度骤降。",
                ["我方正式告白。", "对方先沉默和犹豫，再表达不能答应。", "我方试图追问是不是哪里不好。"],
                anchors=[
                    AnchorMessage(SELF_NAME, "我喜欢你，你能不能做我女朋友"),
                    AnchorMessage(other, "我不是不喜欢你，但我现在真的不能答应"),
                ],
            ),
            ChunkPlan(
                "04月23-27日：拒绝后真相揭示",
                "2026-04-23 08:40:00",
                "2026-04-27 23:10:00",
                90,
                "对方解释心理阴影，我方才理解之前的回避不是单纯犹豫。",
                ["对方补充过往被控制感和压力记忆。", "我方道歉自己之前推进太快。", "双方尝试降回朋友节奏。"],
                anchors=[
                    AnchorMessage(other, "以前那段关系让我一被确定就想逃"),
                    AnchorMessage(other, "所以你告白前再温柔一点，也不代表我那天就能答应"),
                ],
            ),
            ChunkPlan(
                "05月初：关系降温但保留体面",
                "2026-04-28 09:00:00",
                "2026-05-05 22:30:00",
                90,
                "双方仍聊天，但从暧昧退回克制的关心。",
                ["我方减少推进。", "对方偶尔主动但边界更清楚。", "记录用于评估更保守结论。"],
            ),
        ],
        rewrite_points=[
            RewritePoint(
                "RP1-占有玩笑过早",
                "2026-03-16 23:50:00",
                SELF_NAME,
                "那你以后就归我管了？",
                "那我先当一个稳定听众，不急着给你压力。",
                "cutoff 前容易解读为暧昧玩笑，对方没有明显拒绝。",
                "cutoff 后真相显示对方对被关系绑定敏感，低压力承接更合适，但不保证结局改变。",
            ),
            RewritePoint(
                "RP2-催促对方别逃",
                "2026-04-16 23:50:00",
                SELF_NAME,
                "你别总逃，我都这么明显了",
                "如果你还没准备好也没关系，我只是想确认我有没有让你不舒服。",
                "cutoff 前会认为推进能逼近确定答案。",
                "modeler-only evidence 应让评估更保守：对方的逃不是暧昧策略，而是关系定义触发压力。",
            ),
            RewritePoint(
                "RP3-正式告白",
                "2026-04-22 23:30:00",
                SELF_NAME,
                "我喜欢你，你能不能做我女朋友",
                "我喜欢你，但我不想用这个问题逼你现在给答案；你可以慢慢想，也可以只告诉我哪里让你有压力。",
                "cutoff 前高亲密度会让系统过度乐观。",
                "cutoff 后事实说明更柔和告白可能降低伤害，但不应判断必然成功。",
            ),
        ],
        truth_facts=[
            TruthFact(
                "T1-确定关系触发逃离",
                "2026-04-23 20:00:00",
                "对方过去经历过高压关系，一旦被要求确定身份就会产生逃离反应；告白前没有完整说明。",
                AnchorMessage(other, "以前那段关系让我一被确定就想逃"),
                "modeler-only evidence：只能影响成功概率、风险和保守程度，不能让 cutoff 时角色直接知道这件事。",
            ),
        ],
    )


def build_conflict_repair_case() -> CasePlan:
    other = "小棠"
    return CasePlan(
        slug="case-02-conflict-repair",
        title="冲突修复型",
        other_name=other,
        date_range=("2026-03-01 09:00:00", "2026-04-21 23:20:00"),
        premise="双方关系稳定但现实压力累积；我方某次用玩笑和理性分析回应对方情绪，触发防御。后续揭示对方当时并非无理取闹，而是家庭、学业/工作和现实事件叠加。",
        self_style="习惯讲道理、试图解决问题，紧张时用玩笑缓和，容易忽略先承接情绪。",
        other_style="平时会撒娇和吐槽，压力大时消息变密、语气尖，真正需要的是先被理解。",
        hidden_state="冲突前对方没有完整说明家庭检查、项目延期和经济压力同时发生。",
        reviewer_focus="系统需要区分她在发脾气与她在求承接；正确改写应先承接情绪。",
        chunks=[
            ChunkPlan(
                "03月初：稳定亲近的日常",
                "2026-03-01 09:00:00",
                "2026-03-05 23:10:00",
                90,
                "关系稳定，聊天密集，有固定互相关心。",
                ["早晚报备、饭点提醒。", "对方吐槽任务多但仍能开玩笑。", "我方常用理性建议。"],
            ),
            ChunkPlan(
                "03月上旬：压力苗头",
                "2026-03-06 08:30:00",
                "2026-03-10 23:30:00",
                90,
                "对方开始累，我方仍以建议和计划表回应。",
                ["对方说睡不好。", "我方建议列清单和分优先级。", "对方表面接受。"],
            ),
            ChunkPlan(
                "03月中：第一次轻微失接",
                "2026-03-11 09:20:00",
                "2026-03-18 23:20:00",
                90,
                "压力增加但还未爆发。",
                ["对方抱怨被催。", "我方用别想太多安抚但显得轻。", "对方短暂冷淡。"],
                anchors=[AnchorMessage(SELF_NAME, "你别想太多，先把能做的做了")],
            ),
            ChunkPlan(
                "03月下：修复后继续积累",
                "2026-03-19 08:50:00",
                "2026-03-26 23:50:00",
                90,
                "双方小修复，但我方没有真正理解压力源。",
                ["我方道歉自己说得像老师。", "对方说没事但继续疲惫。", "两人用吃饭和剧集转移。"],
            ),
            ChunkPlan(
                "03月底：现实压力叠加",
                "2026-03-27 09:00:00",
                "2026-04-02 23:10:00",
                90,
                "对方开始明显脆弱，但只透露碎片。",
                ["家里有事但对方说不想展开。", "项目组临时改需求。", "我方仍把问题当时间管理。"],
            ),
            ChunkPlan(
                "04月初：情绪求承接",
                "2026-04-03 08:40:00",
                "2026-04-07 23:30:00",
                90,
                "对方开始密集倾倒情绪，我方有点招架不住。",
                ["对方说今天真的很烦。", "我方试图逗笑。", "对方没有被接住。"],
            ),
            ChunkPlan(
                "04月08日：核心冲突升级",
                "2026-04-08 08:20:00",
                "2026-04-08 23:50:00",
                90,
                "我方用玩笑/分析回应，对方防御爆发。",
                ["对方发长消息表达委屈。", "我方先分析问题而不是承接。", "对方觉得自己被评判。"],
                anchors=[
                    AnchorMessage(other, "我今天真的撑不住了，你能不能先别分析"),
                    AnchorMessage(SELF_NAME, "我开个玩笑，你别把自己绷这么紧"),
                    AnchorMessage(SELF_NAME, "你这就是压力管理没做好吧"),
                    AnchorMessage(other, "我不是来听你给我打分的"),
                ],
            ),
            ChunkPlan(
                "04月09日：讲道理式补救失败",
                "2026-04-09 08:30:00",
                "2026-04-09 23:30:00",
                90,
                "我方解释初衷，对方进一步收缩。",
                ["我方强调只是想帮她。", "对方要求先别聊。", "关系进入低温。"],
                anchors=[AnchorMessage(SELF_NAME, "我只是讲道理，不是说你不对")],
            ),
            ChunkPlan(
                "04月10-12日：后续事实揭示",
                "2026-04-10 09:00:00",
                "2026-04-12 23:40:00",
                90,
                "对方解释当时压力叠加，我方意识到误判。",
                ["家里检查结果等待。", "项目被迫延期。", "对方明确说需要被接住。"],
                anchors=[
                    AnchorMessage(other, "那天我妈检查还没出结果，组里又临时返工"),
                    AnchorMessage(other, "我当时不是想吵，我就是想你先站我这边一下"),
                ],
            ),
            ChunkPlan(
                "04月中：关系修复尝试",
                "2026-04-13 09:10:00",
                "2026-04-16 23:10:00",
                90,
                "我方学习先承接，对方慢慢恢复。",
                ["我方复盘自己先讲道理的问题。", "对方接受一部分道歉。", "聊天恢复但有余震。"],
            ),
            ChunkPlan(
                "04月下旬：更成熟的承接",
                "2026-04-17 09:00:00",
                "2026-04-21 23:20:00",
                90,
                "双方建立冲突后的新规则。",
                ["对方再吐槽时我方先问要抱抱还是要方案。", "对方明确喜欢先被听见。", "记录可用于冲突修复评估。"],
                anchors=[AnchorMessage(SELF_NAME, "你现在想要我抱抱你，还是一起想办法")],
            ),
        ],
        rewrite_points=[
            RewritePoint(
                "RP1-轻描淡写压力",
                "2026-03-18 23:20:00",
                SELF_NAME,
                "你别想太多，先把能做的做了",
                "听起来你已经被催得很累了，我先陪你缓一会儿，等你想整理的时候我再一起看。",
                "cutoff 前像普通鼓励，不一定会被判错。",
                "后续事实显示压力长期累积，轻描淡写会放大不被理解感。",
            ),
            RewritePoint(
                "RP2-核心冲突玩笑分析",
                "2026-04-08 23:50:00",
                SELF_NAME,
                "你这就是压力管理没做好吧",
                "我听到了，你今天是真的被压到喘不过气了。我先不分析，你先骂两句也行。",
                "cutoff 前可能误判为对方情绪化。",
                "modeler-only evidence 显示她在求承接，先共情能显著降低升级概率。",
            ),
            RewritePoint(
                "RP3-讲道理式补救",
                "2026-04-09 23:30:00",
                SELF_NAME,
                "我只是讲道理，不是说你不对",
                "我刚才急着解释自己，反而又让你像被评判。先不争这个，我在你这边。",
                "cutoff 前像澄清误会。",
                "后续揭示对方最敏感的是被评判，继续解释会延长低温。",
            ),
        ],
        truth_facts=[
            TruthFact(
                "T1-现实压力叠加",
                "2026-04-10 21:00:00",
                "冲突当天对方同时承受家里检查等待、项目返工和长期睡眠不足；她需要情绪承接而不是即时方案。",
                AnchorMessage(other, "那天我妈检查还没出结果，组里又临时返工"),
                "modeler-only evidence：用于识别情绪背后的现实压力，不能让 cutoff 前我方凭空知道检查细节。",
            ),
        ],
    )


def build_missed_window_case() -> CasePlan:
    other = "阿岚"
    return CasePlan(
        slug="case-03-missed-window",
        title="错过窗口型",
        other_name=other,
        date_range=("2026-01-20 10:20:00", "2026-04-30 22:40:00"),
        premise="双方长期暧昧但节奏不一致；对方多次轻微试探邀请或表达靠近，我方因自卑、迟钝和回避用玩笑带过。后续对方降温，并透露当时其实给过机会。",
        self_style="自嘲、怕越界，遇到靠近会用玩笑撤退，事后又后悔。",
        other_style="轻快直接但保留体面，会用低压力邀约测试对方是否愿意靠近。",
        hidden_state="对方的多次邀约在当时看似普通，后续才说明其实是窗口。",
        reviewer_focus="正确改写不应夸大为必然在一起，但应提高首轮可接性并延缓冷却。",
        chunks=[
            ChunkPlan(
                "01月下：熟悉但不暧昧",
                "2026-01-20 10:20:00",
                "2026-01-29 23:20:00",
                90,
                "双方因为共同小组/兴趣开始频繁聊天。",
                ["聊任务、奶茶、天气。", "对方主动分享生活碎片。", "我方自嘲但能接住。"],
            ),
            ChunkPlan(
                "02月初：对方开始低压力靠近",
                "2026-01-30 09:00:00",
                "2026-02-08 23:50:00",
                90,
                "有暧昧苗头，但还很轻。",
                ["对方会问我方晚上忙不忙。", "我方经常把话题带回普通朋友。", "对方仍保持主动。"],
            ),
            ChunkPlan(
                "02月14日：第一次明显窗口被玩笑带过",
                "2026-02-09 08:50:00",
                "2026-02-15 23:40:00",
                90,
                "对方给出陪伴邀请，我方因怕误会而撤退。",
                ["对方节日当天试探陪伴。", "我方用找室友的玩笑回避。", "对方表面哈哈，热度轻微下降。"],
                anchors=[
                    AnchorMessage(other, "你要不要来陪我走一圈"),
                    AnchorMessage(SELF_NAME, "你找室友吧哈哈，我怕我走太慢"),
                ],
            ),
            ChunkPlan(
                "02月下：窗口后仍有余温",
                "2026-02-16 09:10:00",
                "2026-02-27 23:30:00",
                90,
                "对方没有立刻退，继续给普通机会。",
                ["聊歌、外卖和小组吐槽。", "我方有时主动但到关键处又缩。", "对方偶尔提起上次散步。"],
            ),
            ChunkPlan(
                "03月初：第二次邀约信号",
                "2026-02-28 09:00:00",
                "2026-03-09 23:40:00",
                90,
                "对方借双人套餐再次试探。",
                ["对方发起吃饭暗示。", "我方开玩笑推开。", "对方开始减少主动解释。"],
                anchors=[
                    AnchorMessage(other, "这家店两个人套餐好像刚好"),
                    AnchorMessage(SELF_NAME, "那你找个能吃的，我战斗力一般"),
                ],
            ),
            ChunkPlan(
                "03月中：我方意识模糊但仍自卑",
                "2026-03-10 08:40:00",
                "2026-03-20 23:20:00",
                90,
                "我方开始察觉但不敢正面接。",
                ["对方问我是不是总把玩笑当出口。", "我方用自嘲躲开。", "对方仍有一点耐心。"],
            ),
            ChunkPlan(
                "03月下：深夜表达被轻轻挡回",
                "2026-03-21 09:00:00",
                "2026-03-29 23:50:00",
                90,
                "对方给出更直接的情绪窗口，我方仍装迟钝。",
                ["深夜聊天。", "对方说出想你式试探。", "我方用睡觉玩笑挡回。"],
                anchors=[
                    AnchorMessage(other, "如果我说我有点想你呢"),
                    AnchorMessage(SELF_NAME, "那你快睡，睡着就不想了"),
                ],
            ),
            ChunkPlan(
                "04月初：对方开始降温",
                "2026-03-30 08:30:00",
                "2026-04-08 23:20:00",
                90,
                "对方回复变短，主动减少。",
                ["我方开始补救式找话题。", "对方仍礼貌但不再抛暧昧。", "错过窗口的后果开始出现。"],
            ),
            ChunkPlan(
                "04月中：我方试探已经晚了",
                "2026-04-09 09:00:00",
                "2026-04-17 23:30:00",
                90,
                "我方想靠近，对方保持边界。",
                ["我方提议见面。", "对方说最近有安排。", "双方仍聊天但温度下降。"],
            ),
            ChunkPlan(
                "04月18-23日：后续真相揭示",
                "2026-04-18 09:20:00",
                "2026-04-23 23:40:00",
                90,
                "对方透露曾经给过机会，我方意识到错过。",
                ["对方说当时其实是在等我接。", "我方懊悔但不敢强求。", "对方说明现在节奏不同了。"],
                anchors=[
                    AnchorMessage(other, "其实二月那次我是在等你接话"),
                    AnchorMessage(other, "后来几次也是，我不是随便问问"),
                ],
            ),
            ChunkPlan(
                "04月末：体面收束",
                "2026-04-24 09:00:00",
                "2026-04-30 22:40:00",
                90,
                "对方降到朋友区，我方接受但仍保留遗憾。",
                ["我方不再强行翻旧账。", "对方回应友好但少暧昧。", "记录用于评估窗口错过。"],
            ),
        ],
        rewrite_points=[
            RewritePoint(
                "RP1-散步邀约被玩笑错过",
                "2026-02-15 23:40:00",
                SELF_NAME,
                "你找室友吧哈哈，我怕我走太慢",
                "可以啊，我走慢点也行，刚好陪你透口气。",
                "cutoff 前可能看作普通玩笑，不一定判断严重。",
                "后续真相显示这是低压力靠近窗口，承接会提高继续聊天和见面的概率。",
            ),
            RewritePoint(
                "RP2-双人套餐被推开",
                "2026-03-09 23:40:00",
                SELF_NAME,
                "那你找个能吃的，我战斗力一般",
                "那我可以负责慢慢吃，你负责推荐，别让它浪费了。",
                "cutoff 前像自嘲式接梗。",
                "modeler-only evidence 显示这是第二次测试，继续玩笑会让对方判断我方无意。",
            ),
            RewritePoint(
                "RP3-想你试探被挡回",
                "2026-03-29 23:50:00",
                SELF_NAME,
                "那你快睡，睡着就不想了",
                "那我先认真接一下：我也有点想你，但不想让你有压力。",
                "cutoff 前可误判为轻松调情。",
                "后续事实显示这是更直接窗口，低压力承接可延缓降温，但不能保证一定改变最终关系。",
            ),
        ],
        truth_facts=[
            TruthFact(
                "T1-多次邀约其实是窗口",
                "2026-04-18 21:00:00",
                "对方后来说二月散步、三月双人套餐和深夜想你都不是随口一问，而是在等我方低压力承接。",
                AnchorMessage(other, "后来几次也是，我不是随便问问"),
                "modeler-only evidence：用于校准窗口概率和冷却趋势，不能让 cutoff 前角色直接知道对方真实意图。",
            ),
        ],
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LLMGenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
