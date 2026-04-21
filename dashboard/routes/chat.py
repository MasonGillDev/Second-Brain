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

            # Handle /clear command
            if text.strip() == "/clear":
                agent.memory.conversation.clear_session()
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

            async def run_agent():
                nonlocal response_text, error_text
                try:
                    response_text = await agent.process(text or "What's in this image?", images=images)
                except Exception as e:
                    error_text = str(e)

            task = asyncio.create_task(run_agent())

            # Poll for tool events while agent runs
            while not task.done():
                await asyncio.sleep(0.1)
                while tool_events:
                    evt = tool_events.pop(0)
                    await send_json({
                        "type": "tool_call",
                        "name": evt["name"],
                        "args": evt["args"],
                    })

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
            else:
                if debug:
                    await send_json({
                        "type": "debug_context",
                        "system_prompt": getattr(agent, "_last_system_prompt", ""),
                        "messages": getattr(agent, "_last_messages", []),
                    })
                await send_json({"type": "response", "text": response_text})
