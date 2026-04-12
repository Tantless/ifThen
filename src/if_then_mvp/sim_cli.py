from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
PAGE_SIZE = 200


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-self-text":
        messages = list_self_text_messages(
            base_url=args.base_url,
            conversation_id=args.conversation_id,
            limit=args.limit,
            keywords=args.keywords or [],
        )
        for item in messages:
            print(
                f'id={item["id"]} seq={item["sequence_no"]} '
                f'time={item["timestamp"]} text={item["content_text"]}'
            )
        return 0

    if args.command == "simulate":
        result = post_json(
            base_url=args.base_url,
            path="/simulations",
            payload={
                "conversation_id": args.conversation_id,
                "target_message_id": args.target_message_id,
                "replacement_content": args.replacement,
                "mode": args.mode,
                "turn_count": args.turn_count,
            },
        )
        print(f'id={result.get("id")} conversation_id={result.get("conversation_id")}')
        print(f'target_message_id={result.get("target_message_id")} mode={result.get("mode")}')
        print(f'turn_count={result.get("turn_count")} status={result.get("status")}')
        print(f'current_stage={result.get("current_stage")} progress_percent={result.get("progress_percent")}')
        print(f'status_message={result.get("status_message")}')
        print(f'result_simulation_id={result.get("result_simulation_id")}')
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulation CLI for If Then MVP")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-self-text", help="List candidate self text messages")
    list_parser.add_argument("--conversation-id", type=int, required=True)
    list_parser.add_argument("--keywords", nargs="*", default=[])
    list_parser.add_argument("--limit", type=int, default=20)

    simulate_parser = subparsers.add_parser("simulate", help="Run a simulation")
    simulate_parser.add_argument("--conversation-id", type=int, required=True)
    simulate_parser.add_argument("--target-message-id", type=int, required=True)
    simulate_parser.add_argument("--replacement", required=True)
    simulate_parser.add_argument("--mode", choices=("single_reply", "short_thread"), default="short_thread")
    simulate_parser.add_argument("--turn-count", type=int, default=4)

    return parser


def list_self_text_messages(
    *,
    base_url: str,
    conversation_id: int,
    limit: int,
    keywords: list[str],
) -> list[dict[str, Any]]:
    normalized_keywords = [item.casefold() for item in keywords if item.strip()]
    matches: list[dict[str, Any]] = []
    after: int | None = None

    while len(matches) < limit:
        page = fetch_messages_page(
            base_url=base_url,
            conversation_id=conversation_id,
            after=after,
            page_size=PAGE_SIZE,
        )
        if not page:
            break

        for message in page:
            if message.get("speaker_role") != "self":
                continue
            if message.get("message_type") != "text":
                continue
            content_text = str(message.get("content_text", ""))
            if normalized_keywords and not any(keyword in content_text.casefold() for keyword in normalized_keywords):
                continue
            matches.append(message)
            if len(matches) >= limit:
                break

        after = max(int(item["sequence_no"]) for item in page)

    return matches[:limit]


def fetch_messages_page(
    *,
    base_url: str,
    conversation_id: int,
    after: int | None,
    page_size: int,
) -> list[dict[str, Any]]:
    params = {"limit": page_size}
    if after is not None:
        params["after"] = after
    query = urlencode(params)
    path = f"/conversations/{conversation_id}/messages?{query}"
    return get_json(base_url=base_url, path=path)


def get_json(*, base_url: str, path: str) -> Any:
    with urlopen(f"{base_url.rstrip('/')}{path}") as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(*, base_url: str, path: str, payload: dict[str, Any]) -> Any:
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
