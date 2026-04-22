"""Memory CRUD and cluster visualization endpoints."""

import time
import config
from quart import Blueprint, request, jsonify, current_app
from dashboard.auth import require_auth

memory_bp = Blueprint("memory", __name__)

VALID_COLLECTIONS = {"long_term", "episodic", "procedural", "documents", "reference", "archive"}


@memory_bp.route("/api/memory/stats")
@require_auth
async def stats():
    vs = current_app.vector_store
    conv = current_app.agent.memory.conversation
    return jsonify({
        "collections": vs.get_stats(),
        "conversation": conv.get_stats(),
    })


@memory_bp.route("/api/memory/<collection>")
@require_auth
async def list_memories(collection):
    if collection not in VALID_COLLECTIONS:
        return jsonify({"error": "invalid collection"}), 400

    vs = current_app.vector_store
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    all_mems = vs.get_all(collection, limit=limit + offset)
    mems = all_mems[offset:offset + limit]

    return jsonify({
        "memories": mems,
        "total": vs.count(collection),
    })


@memory_bp.route("/api/memory/<collection>/search")
@require_auth
async def search_memories(collection):
    if collection not in VALID_COLLECTIONS:
        return jsonify({"error": "invalid collection"}), 400

    q = request.args.get("q", "")
    top_k = request.args.get("top_k", 10, type=int)

    if not q:
        return jsonify({"error": "query required"}), 400

    vs = current_app.vector_store
    results = vs.query(collection, q, top_k=top_k)
    return jsonify({"results": results})


@memory_bp.route("/api/memory/<collection>", methods=["POST"])
@require_auth
async def add_memory(collection):
    if collection not in VALID_COLLECTIONS:
        return jsonify({"error": "invalid collection"}), 400

    data = await request.get_json()
    text = data.get("text", "").strip()
    category = data.get("category", "general")

    if not text:
        return jsonify({"error": "text required"}), 400

    vs = current_app.vector_store
    metadata = {"category": category, "type": "dashboard_added"}
    doc_id = vs.add(collection, text, metadata=metadata)
    return jsonify({"id": doc_id, "status": "created"})


@memory_bp.route("/api/memory/<collection>/<doc_id>", methods=["PUT"])
@require_auth
async def update_memory(collection, doc_id):
    if collection not in VALID_COLLECTIONS:
        return jsonify({"error": "invalid collection"}), 400

    data = await request.get_json()
    new_text = data.get("text", "").strip()

    if not new_text:
        return jsonify({"error": "text required"}), 400

    vs = current_app.vector_store

    # ChromaDB doesn't support update — delete + re-add with same ID
    col = vs.collections[collection]
    try:
        existing = col.get(ids=[doc_id])
        if not existing["ids"]:
            return jsonify({"error": "not found"}), 404
        old_meta = existing["metadatas"][0] if existing["metadatas"] else {}
    except Exception:
        return jsonify({"error": "not found"}), 404

    old_meta["last_modified"] = time.time()
    col.delete(ids=[doc_id])
    col.add(ids=[doc_id], documents=[new_text], metadatas=[old_meta])

    return jsonify({"id": doc_id, "status": "updated"})


@memory_bp.route("/api/memory/<collection>/<doc_id>", methods=["DELETE"])
@require_auth
async def delete_memory(collection, doc_id):
    if collection not in VALID_COLLECTIONS:
        return jsonify({"error": "invalid collection"}), 400

    vs = current_app.vector_store
    vs.delete(collection, doc_id)
    return jsonify({"status": "deleted"})


@memory_bp.route("/api/memory/code/search")
@require_auth
async def search_code_context():
    """Search code_context collection — mirrors what search_code tool returns."""
    q = request.args.get("q", "")
    top_k = request.args.get("top_k", 12, type=int)

    if not q:
        return jsonify({"error": "query required"}), 400

    vs = current_app.vector_store
    if "code_context" not in vs.collections:
        return jsonify({"results": [], "total": 0})

    results = vs.query("code_context", q, top_k=top_k)
    results = [r for r in results if r.get("relevance", 0) >= config.RETRIEVAL_MIN_RELEVANCE_CODE]

    return jsonify({"results": results, "total": vs.count("code_context")})


@memory_bp.route("/api/memory/code/list")
@require_auth
async def list_code_context():
    """List code_context entries."""
    vs = current_app.vector_store
    if "code_context" not in vs.collections:
        return jsonify({"memories": [], "total": 0})

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    all_mems = vs.get_all("code_context", limit=limit + offset)
    mems = all_mems[offset:offset + limit]

    return jsonify({"memories": mems, "total": vs.count("code_context")})


@memory_bp.route("/api/memory/clusters")
@require_auth
async def clusters():
    collection = request.args.get("collection", "long_term")
    threshold = request.args.get("threshold", 0.35, type=float)

    if collection not in VALID_COLLECTIONS:
        return jsonify({"error": "invalid collection"}), 400

    vs = current_app.vector_store
    all_mems = vs.get_all(collection, limit=200)

    if not all_mems:
        return jsonify({"nodes": [], "edges": []})

    nodes = []
    edges_map = {}

    for mem in all_mems:
        nodes.append({
            "id": mem["id"],
            "text": mem["text"][:120],
            "category": mem.get("metadata", {}).get("category", "general"),
            "access_count": mem.get("metadata", {}).get("access_count", 0),
        })

    # Build edges via similarity queries
    for mem in all_mems:
        similar = vs.query(collection, mem["text"], top_k=8)
        for s in similar:
            if s["id"] == mem["id"]:
                continue
            if s["relevance"] < threshold:
                continue
            # Deduplicate edges
            edge_key = tuple(sorted([mem["id"], s["id"]]))
            if edge_key not in edges_map or s["relevance"] > edges_map[edge_key]:
                edges_map[edge_key] = s["relevance"]

    edges = [
        {"source": k[0], "target": k[1], "similarity": v}
        for k, v in edges_map.items()
    ]

    return jsonify({"nodes": nodes, "edges": edges})
