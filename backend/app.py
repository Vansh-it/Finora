"""Lightweight Flask API server exposing LLM-powered endpoints.

Uses a centralized ProviderManager for automatic failover between LLMs.
When one provider hits rate limits, the system seamlessly switches to the
next available provider — the user never sees an interruption.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

# ── Structured pipeline logging ──────────────────────────────────────────────
logger = logging.getLogger("finora.pipeline")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# ── Ensure backend.lib is importable regardless of cwd ────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.provider_manager import generate_text, get_status, get_manager  # noqa: E402
from lib.intent_service import classify_intent  # noqa: E402
from lib.research_orchestrator import create_research_plan  # noqa: E402
from lib.research_session import (  # noqa: E402
    grant_permission, get_session, cancel_session,
    update_session_status, set_session_company_meta,
    set_session_document_registry, set_session_financial_statements,
    set_session_calculated_metrics, set_session_source_registry,
    set_session_verification_results, set_session_executive_summary,
    set_session_market_data, set_session_valuation_metrics,
    set_session_error,
)
from lib.company_resolver import resolve_company  # noqa: E402
from lib.filing_retriever import retrieve_filings  # noqa: E402
from lib.financial_extractor import extract_financials  # noqa: E402
from lib.financial_calculator import calculate_metrics  # noqa: E402
from lib.source_discovery import discover_sources  # noqa: E402
from lib.jina_client import read_url  # noqa: E402
from lib.source_fact_extractor import extract_facts_from_source  # noqa: E402
from lib.source_verifier import verify_sources  # noqa: E402
from lib.dashboard_builder import build_dashboard_payload  # noqa: E402
from lib.executive_summary import generate_executive_summary  # noqa: E402
from lib.twelve_data_client import get_market_snapshot, fetch_historical_price  # noqa: E402
from lib.valuation_engine import calculate_valuation  # noqa: E402
from lib.auth_service import (  # noqa: E402
    sign_up, sign_in, sign_out, get_user_from_token, get_user,
    increment_research_runs, can_use_research,
)
from lib.chat_usage import can_send_message, record_message, get_usage as get_chat_usage  # noqa: E402

app = Flask(__name__)

# ── CORS configuration ────────────────────────────────────────────────────────
# In production, restrict to specific origins. For dev, allow localhost.
_allowed_origins_str = os.environ.get("CORS_ORIGINS", "")
if _allowed_origins_str:
    _allowed_origins = [o.strip() for o in _allowed_origins_str.split(",") if o.strip()]
else:
    # Development defaults
    _allowed_origins = [
        "http://localhost:4321",
        "http://localhost:3000",
        "http://127.0.0.1:4321",
        "http://127.0.0.1:3000",
    ]

CORS(app, origins=_allowed_origins, supports_credentials=True)

# ── Security: max request size (1MB) ──────────────────────────────────────────
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024  # 1MB

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_MESSAGE_LENGTH = 2000
MAX_SESSION_ID_LEN = 128
MAX_PROMPT_LEN = 5000

# Valid session ID format (hex string)
_SESSION_ID_RE = re.compile(r"^[a-f0-9]{32,64}$")


# ── Input validation helpers ──────────────────────────────────────────────────
def _validate_session_id(session_id: str) -> str | None:
    """Validate and sanitize a session ID. Returns error message or None."""
    if not isinstance(session_id, str) or not session_id.strip():
        return "Missing 'session_id' field"
    sid = session_id.strip()
    if len(sid) > MAX_SESSION_ID_LEN:
        return "Invalid session ID"
    if not _SESSION_ID_RE.match(sid):
        return "Invalid session ID format"
    return None


def _get_auth_user():
    """Extract and validate the authenticated user from the request. Returns (user, error_response)."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return None, (jsonify({"error": "Missing Authorization header"}), 401)
    user = get_user_from_token(token)
    if user is None:
        return None, (jsonify({"error": "Invalid or expired session"}), 401)
    return user, None


def _check_session_ownership(session, user):
    """Check that a session belongs to the authenticated user. Returns error response or None."""
    if session.user_id and session.user_id != user.user_id:
        return jsonify({"error": "Access denied"}), 403
    return None


# ── Serve the API test page ──────────────────────────────────────────────────
@app.get("/test")
def test_page():
    """Serve the LLM chat testing page."""
    from flask import send_from_directory
    return send_from_directory(str(Path(__file__).resolve().parent), "api_test.html")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    status = get_status()
    active = status.get("active_provider", "none")
    return jsonify({
        "status": "ok",
        "active_provider": active,
        "providers_available": sum(
            1 for p in status["providers"] if p["available"]
        ),
    })


# ── Main generation endpoint (with automatic failover) ────────────────────────
@app.post("/api/generate")
def api_generate():
    """Send a prompt to the LLM chain with automatic failover."""
    body = request.get_json(silent=True) or {}
    prompt = body.get("prompt", "Say hello in one short sentence.")

    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "Invalid prompt"}), 400
    prompt = prompt[:MAX_PROMPT_LEN]

    manager = get_manager()
    start_time = time.time()

    try:
        status_before = manager.get_status()
        first_available = status_before["active_provider"]

        text = generate_text(prompt)

        status_after = manager.get_status()
        active_after = status_after["active_provider"]
        failover_used = first_available != active_after and first_available != "none"

        elapsed_ms = round((time.time() - start_time) * 1000)

        return jsonify({
            "model": active_after,
            "response": text,
            "failover_used": failover_used,
            "elapsed_ms": elapsed_ms,
            "provider_status": {
                "active": active_after,
                "available_count": sum(
                    1 for p in status_after["providers"] if p["available"]
                ),
            },
        })

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({
            "error": str(exc),
            "provider_status": get_status(),
        }), 502


# ── Intent classification endpoint ────────────────────────────────────────────
@app.post("/api/classify-intent")
def api_classify_intent():
    """Classify a user prompt as 'chat' or 'research'."""
    body = request.get_json(silent=True) or {}
    prompt = body.get("prompt", "")

    if not prompt or not isinstance(prompt, str):
        return jsonify({"error": "Missing 'prompt' field in request body"}), 400
    prompt = prompt[:MAX_PROMPT_LEN]

    try:
        result = classify_intent(prompt)
        return jsonify(result.to_dict())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({
            "error": str(exc),
            "provider_status": get_status(),
        }), 502


# ── Research plan endpoint ─────────────────────────────────────────────────────
@app.post("/api/create-research-plan")
def api_create_research_plan():
    """Create a validated research plan from a classified intent."""
    body = request.get_json(silent=True) or {}
    intent = body.get("intent")

    if not isinstance(intent, dict):
        return jsonify({"error": "Missing or invalid 'intent' object in request body"}), 400

    try:
        plan = create_research_plan(intent)
        return jsonify(plan.to_dict())
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


# ── Grant permission endpoint ──────────────────────────────────────────────────
@app.post("/api/grant-permission")
def api_grant_permission():
    """Grant permission and create a research session. Requires auth + quota."""
    # Auth required
    user, err = _get_auth_user()
    if err:
        return err

    # Check research quota
    quota = can_use_research(user.user_id)
    if not quota["allowed"]:
        return jsonify({
            "error": f"You've used all {quota['limit']} research runs available in this Finora preview.",
            "quota_exhausted": True,
            "remaining": 0,
            "limit": quota["limit"],
        }), 429

    body = request.get_json(silent=True) or {}
    if not body:
        return jsonify({"error": "Missing JSON body"}), 400

    try:
        session = grant_permission(body, user_id=user.user_id)
        return jsonify({
            "session_id": session.session_id,
            "company": session.company,
            "status": session.status,
            "period_mode": session.period_mode,
        })
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400


# ── Research: fetch filings endpoint ──────────────────────────────────────────
@app.post("/api/research/fetch-filings")
def api_fetch_filings():
    """Resolve company and fetch relevant SEC filings."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")

    err = _validate_session_id(session_id)
    if err:
        return jsonify({"error": err}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    if session.status == "cancelled":
        return jsonify({"error": "Session has been cancelled"}), 409

    # Ownership check
    user, auth_err = _get_auth_user()
    if auth_err:
        # Allow unauthenticated for backward compat, but log
        pass
    elif session.user_id and user and session.user_id != user.user_id:
        return jsonify({"error": "Access denied"}), 403

    # Step 1: Resolve company
    logger.info(f"PIPELINE_TRIGGERED session_id={session_id[:12]}... company={session.company}")
    logger.info(f"RESOLVE_COMPANY_START session_id={session_id[:12]}...")
    t0 = __import__('time').time()
    update_session_status(session_id, "resolving_company")
    try:
        company = resolve_company(session.company)
        set_session_company_meta(session_id, company.to_dict())
        update_session_status(session_id, "company_resolved")
        logger.info(f"RESOLVE_COMPANY_END session_id={session_id[:12]}... elapsed={__import__('time').time()-t0:.1f}s cik={company.cik}")
    except ValueError as exc:
        logger.error(f"PIPELINE_FAILED session_id={session_id[:12]}... stage=resolve_company error={exc}")
        set_session_error(session_id, f"Could not resolve company: {exc}")
        return jsonify({
            "error": f"Could not resolve company '{session.company}': {exc}",
            "status": "error",
        }), 404
    except RuntimeError as exc:
        logger.error(f"PIPELINE_FAILED session_id={session_id[:12]}... stage=resolve_company error={exc}")
        set_session_error(session_id, f"SEC connection failed: {exc}")
        return jsonify({
            "error": "Finora could not connect to SEC EDGAR. Please try again later.",
            "status": "error",
        }), 502

    # Step 2: Fetch filings
    logger.info(f"SEC_FILINGS_START session_id={session_id[:12]}...")
    t0 = __import__('time').time()
    update_session_status(session_id, "fetching_filings")
    try:
        registry = retrieve_filings(
            cik=company.cik,
            company_name=company.name,
            ticker=company.ticker,
            period_mode=session.period_mode,
            start_year=session.start_year,
            end_year=session.end_year,
        )
        registry_dict = registry.to_dict()
        set_session_document_registry(session_id, registry_dict)
        update_session_status(session_id, "filings_found")
        logger.info(f"SEC_FILINGS_END session_id={session_id[:12]}... elapsed={__import__('time').time()-t0:.1f}s count={len(registry_dict['documents'])}")

        return jsonify({
            "status": "filings_found",
            "company": registry_dict["company"],
            "period": registry_dict["period"],
            "documents": registry_dict["documents"],
            "document_count": len(registry_dict["documents"]),
        })

    except ValueError as exc:
        logger.error(f"PIPELINE_FAILED session_id={session_id[:12]}... stage=fetch_filings error={exc}")
        set_session_error(session_id, str(exc))
        return jsonify({
            "error": str(exc),
            "status": "error",
            "company": company.to_dict(),
        }), 404
    except RuntimeError as exc:
        logger.error(f"PIPELINE_FAILED session_id={session_id[:12]}... stage=fetch_filings error={exc}")
        set_session_error(session_id, f"SEC request failed: {exc}")
        return jsonify({
            "error": "Finora could not retrieve filings from SEC EDGAR. Please try again later.",
            "status": "error",
        }), 502


# ── Research: extract financials endpoint ─────────────────────────────────────
@app.post("/api/research/extract-financials")
def api_extract_financials():
    """Extract real financial statements from SEC XBRL CompanyFacts."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")

    err = _validate_session_id(session_id)
    if err:
        return jsonify({"error": err}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    if session.status == "cancelled":
        return jsonify({"error": "Session has been cancelled"}), 409

    if not session.company_meta:
        return jsonify({"error": "Company not resolved yet. Run fetch-filings first."}), 400

    cik = session.company_meta.get("cik", "")
    company_name = session.company_meta.get("name", session.company)
    ticker = session.company_meta.get("ticker", "")

    if not cik:
        return jsonify({"error": "No CIK found in session"}), 400

    logger.info(f"XBRL_START session_id={session_id[:12]}...")
    t0 = __import__('time').time()
    update_session_status(session_id, "fetching_xbrl")
    update_session_status(session_id, "extracting_financials")
    try:
        statements = extract_financials(
            cik=cik,
            company_name=company_name,
            ticker=ticker,
            period_mode=session.period_mode,
            start_year=session.start_year,
            end_year=session.end_year,
        )
    except Exception as exc:
        logger.error(f"PIPELINE_FAILED session_id={session_id[:12]}... stage=extract_financials error={exc}")
        set_session_error(session_id, f"Financial extraction failed: {exc}")
        return jsonify({
            "error": "Finora could not extract financial data from SEC filings.",
            "status": "error",
        }), 500

    update_session_status(session_id, "validating_financials")
    statements_dict = statements.to_dict()
    set_session_financial_statements(session_id, statements_dict)
    update_session_status(session_id, "financials_extracted")
    update_session_status(session_id, "ready_for_calculation")
    logger.info(f"XBRL_END session_id={session_id[:12]}... elapsed={__import__('time').time()-t0:.1f}s")

    return jsonify({
        "status": "ready_for_calculation",
        "company": statements_dict["company"],
        "periods": statements_dict["periods"],
        "income_statement": statements_dict["income_statement"],
        "balance_sheet": statements_dict["balance_sheet"],
        "cash_flow": statements_dict["cash_flow"],
        "additional": statements_dict["additional"],
        "metadata": statements_dict["metadata"],
    })


# ── Research: calculate metrics endpoint ─────────────────────────────────
@app.post("/api/research/calculate-metrics")
def api_calculate_metrics():
    """Calculate financial metrics from extracted financial statements."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")

    err = _validate_session_id(session_id)
    if err:
        return jsonify({"error": err}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    if session.status == "cancelled":
        return jsonify({"error": "Session has been cancelled"}), 409

    if not session.financial_statements:
        return jsonify({"error": "Financial statements not extracted yet."}), 400

    logger.info(f"METRICS_START session_id={session_id[:12]}...")
    t0 = __import__('time').time()
    update_session_status(session_id, "calculating_metrics")
    try:
        metrics = calculate_metrics(session.financial_statements)
    except Exception as exc:
        logger.error(f"PIPELINE_FAILED session_id={session_id[:12]}... stage=calculate_metrics error={exc}")
        set_session_error(session_id, f"Metric calculation failed: {exc}")
        return jsonify({
            "error": "Finora could not calculate financial metrics.",
            "status": "error",
        }), 500

    update_session_status(session_id, "validating_metrics")
    set_session_calculated_metrics(session_id, metrics)
    update_session_status(session_id, "metrics_calculated")
    update_session_status(session_id, "ready_for_analysis")
    logger.info(f"METRICS_END session_id={session_id[:12]}... elapsed={__import__('time').time()-t0:.1f}s")

    return jsonify({
        "status": "ready_for_analysis",
        "company": metrics["company"],
        "periods": metrics["periods"],
        "annual_metrics": metrics["annual_metrics"],
        "growth_metrics": metrics["growth_metrics"],
        "cagr_metrics": metrics["cagr_metrics"],
        "metadata": metrics["metadata"],
    })


# ── Research: discover sources endpoint ────────────────────────────────────────
@app.post("/api/research/discover-sources")
def api_discover_sources():
    """Discover authoritative company financial sources using Tavily + SEC."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")

    err = _validate_session_id(session_id)
    if err:
        return jsonify({"error": err}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    if session.status == "cancelled":
        return jsonify({"error": "Session has been cancelled"}), 409

    if not session.company_meta:
        return jsonify({"error": "Company not resolved yet."}), 400

    company_name = session.company_meta.get("name", session.company)
    ticker = session.company_meta.get("ticker", "")

    logger.info(f"TAVILY_START session_id={session_id[:12]}...")
    t0 = __import__('time').time()
    update_session_status(session_id, "discovering_sources")
    update_session_status(session_id, "filtering_sources")
    update_session_status(session_id, "validating_sources")

    try:
        registry = discover_sources(
            company_name=company_name,
            ticker=ticker,
            period_mode=session.period_mode,
            start_year=session.start_year,
            end_year=session.end_year,
            sec_registry=session.document_registry,
        )
    except Exception as exc:
        sec_only = {
            "company": {"name": company_name, "ticker": ticker},
            "period": {
                "mode": session.period_mode,
                "start_year": session.start_year,
                "end_year": session.end_year,
                "label": "Latest" if session.period_mode == "latest" else f"FY{session.start_year}–FY{session.end_year}",
            },
            "sources": [],
            "metadata": {
                "total_sources": 0,
                "sec_sources": 0,
                "company_sources": 0,
                "third_party_sources": 0,
                "queries_used": 0,
                "tavily_searches": 0,
                "tavily_error": str(exc),
                "fallback": "SEC-only",
            },
        }
        if session.document_registry and "documents" in session.document_registry:
            for doc in session.document_registry["documents"]:
                sec_only["sources"].append({
                    "source_id": doc.get("document_id", "sec_unknown"),
                    "source_type": doc.get("form", "filing").lower(),
                    "authority": "regulatory",
                    "provider": "SEC EDGAR",
                    "url": doc.get("source_url", ""),
                    "title": f"{doc.get('form', 'Filing')} - {company_name}",
                    "period": "Latest" if session.period_mode == "latest" else f"FY{session.start_year}–FY{session.end_year}",
                    "trust_tier": 1,
                    "status": "verified",
                })
            sec_only["metadata"]["total_sources"] = len(sec_only["sources"])
            sec_only["metadata"]["sec_sources"] = len(sec_only["sources"])
        registry = sec_only

    set_session_source_registry(session_id, registry)
    update_session_status(session_id, "sources_discovered")
    update_session_status(session_id, "ready_for_reading")
    logger.info(f"TAVILY_END session_id={session_id[:12]}... elapsed={__import__('time').time()-t0:.1f}s sources={len(registry.get('sources', []))}")

    return jsonify({
        "status": "sources_discovered",
        "sources": registry["sources"],
        "metadata": registry["metadata"],
    })


# ── Research: read + verify sources endpoint ──────────────────────────────────
@app.post("/api/research/read-verify-sources")
def api_read_verify_sources():
    """Read trusted sources with Jina and cross-verify against SEC."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")

    err = _validate_session_id(session_id)
    if err:
        return jsonify({"error": err}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    if session.status == "cancelled":
        return jsonify({"error": "Session has been cancelled"}), 409

    if not session.source_registry:
        return jsonify({"error": "Source registry not available."}), 400

    if not session.financial_statements:
        return jsonify({"error": "Financial statements not extracted."}), 400

    company_name = session.company_meta.get("name", session.company) if session.company_meta else session.company
    ticker = session.company_meta.get("ticker", "") if session.company_meta else ""

    sources = session.source_registry.get("sources", [])
    readable_sources = [
        s for s in sources
        if s.get("authority") != "regulatory"
        and s.get("trust_tier", 3) <= 2
        and s.get("url", "")
    ]
    readable_sources = readable_sources[:5]

    all_facts: list[dict] = []
    all_commentary: list[dict] = []
    sources_read = 0
    jina_errors: list[str] = []

    logger.info(f"JINA_START session_id={session_id[:12]}... sources_to_read={len(readable_sources)}")
    t0 = __import__('time').time()
    update_session_status(session_id, "reading_sources")

    for source in readable_sources:
        url = source.get("url", "")
        if not url or "sec.gov" in url:
            continue

        try:
            read_result = read_url(url)
        except Exception as exc:
            jina_errors.append(f"{url}: {exc}")
            continue

        content = read_result.get("content", "")
        if not content or read_result.get("status") == "error":
            continue

        sources_read += 1
        update_session_status(session_id, "extracting_source_facts")

        try:
            extraction = extract_facts_from_source(
                content=content,
                company_name=company_name,
                ticker=ticker,
                period=session.period_mode,
                source_id=source.get("source_id", ""),
                source_url=url,
                source_provider=source.get("provider", ""),
                source_type=source.get("source_type", ""),
            )
            all_facts.extend(extraction.get("facts", []))
            all_commentary.extend(extraction.get("commentary", []))
        except Exception:
            continue

    update_session_status(session_id, "cross_checking_sources")

    try:
        verification = verify_sources(
            sec_statements=session.financial_statements,
            external_facts=all_facts,
            commentary=all_commentary,
            company_name=company_name,
            ticker=ticker,
        )
    except Exception as exc:
        verification = {
            "verifications": [],
            "summary": {
                "total_compared": 0, "exact_matches": 0, "within_tolerance": 0,
                "mismatches": 0, "not_comparable": 0, "missing_external": 0, "missing_sec": 0,
            },
            "management_commentary": all_commentary,
            "primary_source": "SEC XBRL",
            "error": str(exc),
        }

    verification["sources_read"] = sources_read
    verification["jina_errors"] = jina_errors
    set_session_verification_results(session_id, verification)
    update_session_status(session_id, "verification_complete")
    update_session_status(session_id, "ready_for_dashboard")
    logger.info(f"JINA_END session_id={session_id[:12]}... elapsed={__import__('time').time()-t0:.1f}s sources_read={sources_read}")

    # ── Increment research quota on successful completion ──
    if session.user_id:
        increment_research_runs(session.user_id)

    summary = verification.get("summary", {})
    return jsonify({
        "status": "verification_complete",
        "sources_read": sources_read,
        "metrics_verified": summary.get("total_compared", 0),
        "mismatches": summary.get("mismatches", 0),
        "verifications": verification["verifications"],
        "commentary": verification.get("management_commentary", []),
        "summary": summary,
    })


# ── Research: generate executive summary endpoint ────────────────────────────
@app.post("/api/research/generate-summary")
def api_generate_summary():
    """Generate a professional executive summary from the completed research."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")

    err = _validate_session_id(session_id)
    if err:
        return jsonify({"error": err}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    if session.status == "cancelled":
        return jsonify({"error": "Session has been cancelled"}), 409

    if not session.financial_statements:
        return jsonify({"error": "Financial statements not available."}), 400

    logger.info(f"SUMMARY_START session_id={session_id[:12]}...")
    t0 = __import__('time').time()
    update_session_status(session_id, "generating_analysis")

    try:
        summary = generate_executive_summary(session.to_dict())
    except Exception as exc:
        fallback = {
            "executive_overview": "AI analysis is unavailable for this research session.",
            "highlights": [],
            "growth_analysis": "",
            "profitability_analysis": "",
            "cash_flow_analysis": "",
            "balance_sheet_analysis": "",
            "watch_items": [],
            "management_commentary_summary": "",
            "data_quality_note": _build_fallback_quality_note(session),
            "_metadata": {"error": str(exc), "fallback": True},
        }
        set_session_executive_summary(session_id, fallback)
        update_session_status(session_id, "analysis_complete")
        update_session_status(session_id, "ready_for_dashboard")
        return jsonify({
            "status": "analysis_complete",
            "executive_summary": fallback,
            "warning": "AI summary generation failed. Dashboard data is still available.",
        })

    update_session_status(session_id, "validating_analysis")
    set_session_executive_summary(session_id, summary)
    update_session_status(session_id, "analysis_complete")
    update_session_status(session_id, "ready_for_dashboard")
    logger.info(f"SUMMARY_END session_id={session_id[:12]}... elapsed={__import__('time').time()-t0:.1f}s")
    logger.info(f"PIPELINE_COMPLETE session_id={session_id[:12]}...")

    return jsonify({
        "status": "analysis_complete",
        "executive_summary": summary,
    })


def _build_fallback_quality_note(session) -> str:
    """Build a deterministic quality note for fallback."""
    parts = ["Primary financial data: SEC XBRL."]
    ver = session.verification_results or {}
    summary = ver.get("summary", {})
    cross = summary.get("exact_matches", 0) + summary.get("within_tolerance", 0)
    if cross > 0:
        parts.append(f"{cross} metric{'s' if cross != 1 else ''} cross-verified.")
    parts.append("AI analysis generation failed — financial data remains available.")
    return " ".join(parts)


# ── Research: calculate valuation endpoint ────────────────────────────────────
@app.post("/api/research/calculate-valuation")
def api_calculate_valuation():
    """Fetch market data and calculate valuation multiples."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")

    err = _validate_session_id(session_id)
    if err:
        return jsonify({"error": err}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    if session.status == "cancelled":
        return jsonify({"error": "Session has been cancelled"}), 409

    if not session.calculated_metrics:
        return jsonify({"error": "Metrics not calculated yet."}), 400

    logger.info(f"MARKET_DATA_START session_id={session_id[:12]}...")
    t0 = __import__('time').time()
    # Step 1: Fetch market data
    update_session_status(session_id, "fetching_market_data")
    ticker = session.company_meta.get("ticker", "") if session.company_meta else ""
    if not ticker:
        return jsonify({"error": "No ticker available in session."}), 400

    period_mode = session.period_mode
    end_year = session.end_year

    try:
        if period_mode == "specified" and end_year:
            # Historical: fetch price aligned to fiscal period end
            from lib.valuation_engine import resolve_financial_period_end
            target_period = f"FY{end_year}"
            resolved = resolve_financial_period_end(session.financial_statements or {}, target_period)
            target_date = resolved.get("period_end")
            if not target_date:
                market_data = {
                    "ticker": ticker,
                    "name": session.company_meta.get("name", "") if session.company_meta else "",
                    "exchange": "", "currency": "USD",
                    "price": None, "price_date": "",
                    "previous_close": None, "percent_change": None,
                    "shares_outstanding": None, "market_cap": None,
                    "source": "Twelve Data",
                    "error": f"Cannot determine fiscal period-end date for {target_period}",
                    "fallback": True, "historical": True,
                }
                set_session_market_data(session_id, market_data)
                update_session_status(session_id, "calculating_valuation")
                session_data = session.to_dict()
                session_data["market_data"] = market_data
                result = {
                    "market_data": market_data,
                    "valuation_metrics": {},
                    "period_alignment": {"financial_period": target_period, "alignment_status": "unavailable", "note": f"Historical valuation unavailable: could not determine fiscal period-end date for {target_period}"},
                    "is_financial_institution": False,
                }
                set_session_valuation_metrics(session_id, result)
                update_session_status(session_id, "valuation_complete")
                return jsonify({"status": "valuation_complete", **result})
            hist = fetch_historical_price(ticker, target_date)

            market_data = {
                "ticker": ticker,
                "name": session.company_meta.get("name", "") if session.company_meta else "",
                "exchange": "",
                "currency": "USD",
                "price": None,
                "price_date": "",
                "previous_close": None,
                "percent_change": None,
                "shares_outstanding": None,
                "market_cap": None,
                "source": "Twelve Data",
                "historical": True,
            }

            if hist and hist.get("close"):
                market_data["price"] = hist["close"]
                market_data["price_date"] = hist.get("date", "")
                market_data["alignment_status"] = (
                    "exact_period_end" if hist.get("date") == target_date
                    else "previous_trading_day"
                )
                market_data["target_date"] = target_date
            else:
                market_data["error"] = "Historical price unavailable for requested period"
                market_data["fallback"] = True
        else:
            # Latest: use current quote
            market_data = get_market_snapshot(ticker)

        if market_data.get("error") and not market_data.get("price"):
            market_data = {
                "ticker": ticker,
                "name": session.company_meta.get("name", "") if session.company_meta else "",
                "exchange": "", "currency": "USD",
                "price": None, "price_date": "",
                "previous_close": None, "percent_change": None,
                "shares_outstanding": None, "market_cap": None,
                "source": "Twelve Data",
                "error": market_data.get("error", "Unknown error"),
                "fallback": True,
            }
    except Exception as exc:
        market_data = {
            "ticker": ticker,
            "name": session.company_meta.get("name", "") if session.company_meta else "",
            "exchange": "", "currency": "USD",
            "price": None, "price_date": "",
            "previous_close": None, "percent_change": None,
            "shares_outstanding": None, "market_cap": None,
            "source": "Twelve Data",
            "error": str(exc), "fallback": True,
        }

    set_session_market_data(session_id, market_data)

    # Step 2: Calculate valuation
    update_session_status(session_id, "calculating_valuation")
    session_data = session.to_dict()
    session_data["market_data"] = market_data

    try:
        result = calculate_valuation(session_data)
    except Exception as exc:
        result = {
            "market_data": market_data,
            "valuation_metrics": {},
            "period_alignment": {},
            "is_financial_institution": False,
            "error": str(exc),
        }

    # Step 3: Store
    update_session_status(session_id, "validating_valuation")
    set_session_valuation_metrics(session_id, result)
    update_session_status(session_id, "valuation_complete")
    logger.info(f"MARKET_DATA_END session_id={session_id[:12]}... elapsed={__import__('time').time()-t0:.1f}s")

    return jsonify({
        "status": "valuation_complete",
        "market_data": result.get("market_data", {}),
        "valuation_metrics": result.get("valuation_metrics", {}),
        "period_alignment": result.get("period_alignment", {}),
        "is_financial_institution": result.get("is_financial_institution", False),
    })


# ── Get session endpoint ─────────────────────────────────────────────────────
@app.get("/api/session/<session_id>")
def api_get_session(session_id: str):
    """Look up an existing research session by ID."""
    if not _SESSION_ID_RE.match(session_id):
        return jsonify({"error": "Invalid session ID"}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session.to_dict())


# ── Research result endpoint (dashboard payload) ─────────────────────────────
@app.get("/api/research/result/<session_id>")
def api_research_result(session_id: str):
    """Return the universal dashboard payload for a completed research session."""
    if not _SESSION_ID_RE.match(session_id):
        return jsonify({"error": "Invalid session ID"}), 400

    session = get_session(session_id)
    if session is None:
        return jsonify({"error": "Session not found"}), 404

    if session.status == "cancelled":
        return jsonify({"error": "Session has been cancelled"}), 409

    if session.status == "error":
        return jsonify({"error": session.error or "Research encountered an error"}), 500

    if not session.financial_statements:
        return jsonify({"error": "Research not yet complete. Please wait."}), 202

    try:
        payload = build_dashboard_payload(session.to_dict())
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": f"Failed to build dashboard: {exc}"}), 500


# ── Cancel session endpoint ──────────────────────────────────────────────────
@app.post("/api/cancel-session")
def api_cancel_session():
    """Cancel an active research session."""
    body = request.get_json(silent=True) or {}
    session_id = body.get("session_id", "")

    err = _validate_session_id(session_id)
    if err:
        return jsonify({"error": err}), 400

    cancelled = cancel_session(session_id)
    if not cancelled:
        return jsonify({"error": "Session not found"}), 404

    return jsonify({"session_id": session_id, "status": "cancelled"})


# ── Research quota endpoint ──────────────────────────────────────────────────
@app.get("/api/research/quota")
def api_research_quota():
    """Get the current research quota for the authenticated user."""
    user, err = _get_auth_user()
    if err:
        return err
    quota = can_use_research(user.user_id)
    return jsonify(quota)


# ── Legacy endpoint (backwards compatibility) ─────────────────────────────────
@app.post("/api/test-gemini")
def test_gemini():
    """Legacy endpoint — redirects to /api/generate for backwards compat."""
    body = request.get_json(silent=True) or {}
    prompt = body.get("prompt", "Say hello in one short sentence.")

    try:
        text = generate_text(prompt)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({
            "error": str(exc),
            "provider_status": get_status(),
        }), 502

    return jsonify({
        "model": "auto-failover",
        "response": text,
        "provider_status": get_status(),
    })


# ── Chat endpoint (main frontend chat) ──────────────────────────────────────
FINORA_SYSTEM_PROMPT = (
    "You are Finora, a professional financial analyst AI assistant. "
    "You help users understand public companies, financial statements, SEC filings, "
    "accounting, markets, and research. "
    "Identify yourself as Finora. Be concise and professional. "
    "Never fabricate financial figures. "
    "Never claim access to private or company-confidential information. "
    "Never pretend a research operation has been completed when it has not. "
    "You are especially useful for finance, company analysis, and research."
)


@app.post("/api/chat")
def api_chat():
    """Send a chat message through the LLM."""
    body = request.get_json(silent=True) or {}
    message = body.get("message", "")
    history = body.get("history", [])

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Missing or empty 'message' field"}), 400

    message = message.strip()

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "error": f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters."
        }), 400

    if not isinstance(history, list):
        return jsonify({"error": "'history' must be an array"}), 400

    # Limit history to prevent abuse
    history = history[-10:]

    prompt_parts = [f"System: {FINORA_SYSTEM_PROMPT}"]

    for msg in history:
        role = msg.get("role", "user")
        content = str(msg.get("content", ""))[:500]
        if role in ("user", "assistant"):
            label = "User" if role == "user" else "Assistant"
            prompt_parts.append(f"{label}: {content}")

    prompt_parts.append(f"User: {message}")
    prompt_parts.append("Assistant:")
    prompt = "\n".join(prompt_parts)

    manager = get_manager()
    start_time = time.time()

    try:
        status_before = manager.get_status()
        first_available = status_before["active_provider"]

        text = manager.generate_text(prompt)

        status_after = manager.get_status()
        active_after = status_after["active_provider"]

        elapsed_ms = round((time.time() - start_time) * 1000)

        return jsonify({
            "response": text,
            "model_used": active_after,
            "status": "success",
            "elapsed_ms": elapsed_ms,
        })

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError:
        return jsonify({
            "error": "Finora is temporarily unable to respond. Please try again shortly.",
            "status": "error",
        }), 502


# ── Provider status endpoint (monitoring/debugging) ───────────────────────────
@app.get("/api/provider-status")
def provider_status():
    """Return the health and status of all configured LLM providers."""
    return jsonify(get_status())


# ── Legacy alias ──────────────────────────────────────────────────────────────
@app.get("/api/key-status")
def key_status():
    """Legacy alias for /api/provider-status."""
    return jsonify(get_status())


# ── Auth endpoints ──────────────────────────────────────────────────────────
@app.post("/api/auth/signup")
def api_signup():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    password = body.get("password", "")
    name = body.get("name", "")

    # Input validation
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Invalid input types"}), 400
    if len(email) > 254:
        return jsonify({"error": "Email too long"}), 400
    if len(password) > 128:
        return jsonify({"error": "Password too long"}), 400
    if len(name) > 100:
        return jsonify({"error": "Name too long"}), 400

    try:
        result = sign_up(email, password, name)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/auth/signin")
def api_signin():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "")
    password = body.get("password", "")

    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Invalid input types"}), 400

    try:
        result = sign_in(email, password)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/auth/signout")
def api_signout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "Missing Authorization header"}), 401
    sign_out(token)
    return jsonify({"status": "signed_out"})


@app.get("/api/auth/me")
def api_auth_me():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "Missing Authorization header"}), 401
    user = get_user_from_token(token)
    if user is None:
        return jsonify({"error": "Invalid or expired session"}), 401
    return jsonify(user.to_public_dict())


# ── Chat usage endpoints ────────────────────────────────────────────────────
@app.get("/api/chat/usage")
def api_chat_usage():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "Missing Authorization header"}), 401
    user = get_user_from_token(token)
    if user is None:
        return jsonify({"error": "Invalid or expired session"}), 401
    return jsonify(get_chat_usage(user.user_id))


@app.post("/api/chat/send")
def api_chat_send():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "Missing Authorization header"}), 401
    user = get_user_from_token(token)
    if user is None:
        return jsonify({"error": "Invalid or expired session"}), 401

    usage = record_message(user.user_id)
    if not usage["allowed"]:
        return jsonify({
            "error": "You've used today's 15 Finora Chat messages. Your chat allowance will reset automatically.",
            **usage,
        }), 429

    return jsonify(usage)


# ── Error handlers ───────────────────────────────────────────────────────────
@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "Request too large. Maximum size is 1MB."}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=debug)
