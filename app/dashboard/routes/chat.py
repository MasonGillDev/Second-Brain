"""Chat websocket endpoint."""

import asyncio
import json
from quart import Blueprint, websocket, current_app, session

chat_bp = Blueprint("chat", __name__)


@chat_bp.websocket("/ws/chat")
async def chat_ws():
    if not session.get("authenticated"):
        await websocket.close(4001, "unauthorized")
        return

    agent = current_app.agent

    async def send_json(data):
        await websocket.send(json.dumps(data))

    last_thread_id = None

    async def send_thread_info():
        """Tell the UI which thread this chat is in (panel header), and — when
        the thread CHANGED since this connection last looked (resume, /clear,
        reconnect) — include its full transcript so the feed can be rebuilt."""
        nonlocal last_thread_id
        threads = agent.memory.threads
        if threads is None:
            return
        info = threads.active_info() or {"id": None, "title": None}
        payload = {"type": "thread", **info}
        if info.get("id") != last_thread_id:
            conv = agent.memory.conversation
            payload["history"] = {
                "summary": conv.rolling_summary,
                "messages": conv.display_messages(),
            }
            last_thread_id = info.get("id")
        await send_json(payload)

    await send_thread_info()

    while True:
        raw = await websocket.receive()
        data = json.loads(raw)

        if data.get("type") == "cancel":
            agent.cancel()
            await send_json({"type": "cancelled"})
            continue

        if data.get("type") == "message":
            text = data.get("text", "").strip()
            images = data.get("images")  # list of {data: base64, media_type: str}
            debug = data.get("debug", False)
            if not text and not images:
                continue

            # Handle /clear command. Under threading this is a cold start —
            # the thread is parked (kept + resumable), never deleted. Off-thread
            # via to_thread: parking includes a blocking Haiku title call.
            if text.strip() == "/clear":
                await asyncio.to_thread(agent.memory.cold_start)
                # Thread info first: its history rebuild empties the feed, THEN
                # the confirmation lands in the fresh feed.
                await send_thread_info()
                await send_json({"type": "response", "text": "Cleared. What do you need?"})
                continue

            await send_json({"type": "status", "text": "Processing..."})

            # Set up tool-call streaming
            tool_events = []

            def on_tool(name, args):
                tool_events.append({"name": name, "args": args})

            agent.on_tool_call = on_tool

            # Run process in a task so we can stream tool events
            response_text = None
            error_text = None
            cancelled = False

            async def run_agent():
                nonlocal response_text, error_text
                try:
                    response_text = await agent.process(text or "What's in this image?", images=images, source="dashboard")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    error_text = str(e)

            task = asyncio.create_task(run_agent())

            async def listen_for_cancel():
                """Read incoming websocket messages while the agent runs so a
                cancel click is delivered immediately instead of after completion."""
                nonlocal cancelled
                while not task.done():
                    try:
                        raw = await websocket.receive()
                    except asyncio.CancelledError:
                        return
                    except Exception:
                        return
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if msg.get("type") == "cancel":
                        agent.cancel()
                        cancelled = True
                        await send_json({"type": "cancelled"})

            cancel_listener = asyncio.create_task(listen_for_cancel())

            # Poll for tool events while agent runs
            try:
                while not task.done():
                    await asyncio.sleep(0.1)
                    while tool_events:
                        evt = tool_events.pop(0)
                        await send_json({
                            "type": "tool_call",
                            "name": evt["name"],
                            "args": evt["args"],
                        })
            finally:
                cancel_listener.cancel()
                try:
                    await cancel_listener
                except (asyncio.CancelledError, Exception):
                    pass

            # Flush remaining events
            while tool_events:
                evt = tool_events.pop(0)
                await send_json({
                    "type": "tool_call",
                    "name": evt["name"],
                    "args": evt["args"],
                })

            agent.on_tool_call = None

            if error_text:
                await send_json({"type": "error", "text": error_text})
            elif cancelled:
                # "cancelled" was already sent; suppress duplicate response message
                pass
            else:
                if debug:
                    await send_json({
                        "type": "debug_context",
                        "system_prompt": getattr(agent, "_last_system_prompt", ""),
                        "messages": getattr(agent, "_last_messages", []),
                    })

                await send_json({"type": "response", "text": response_text})
                # The turn may have parked/resumed/created a thread — refresh header
                await send_thread_info()
