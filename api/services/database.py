"""Supabase database operations for SmIA."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from postgrest.exceptions import APIError
from postgrest.types import CountMethod
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Client helpers
# ---------------------------------------------------------------------------

def get_supabase_client(access_token: str | None = None) -> Client:
    """Create a Supabase client.

    If *access_token* is provided the client's Authorization header is set to
    the user's JWT so that Row-Level Security policies are evaluated in the
    context of the authenticated user.  Otherwise the service-role key is used
    which bypasses RLS entirely (useful for server-side operations such as
    looking up bind codes).
    """
    if access_token:
        # Authenticated client – use the anon key as the API key but override
        # the Authorization header with the user's JWT so RLS sees the correct
        # role and user id.
        options = SyncClientOptions(
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return create_client(settings.supabase_url, settings.supabase_anon_key, options)
    else:
        # Service-role client – bypasses RLS.
        key = settings.supabase_service_key or settings.supabase_anon_key
        return create_client(settings.supabase_url, key)


# ---------------------------------------------------------------------------
# Analysis reports
# ---------------------------------------------------------------------------

def save_report_service(report_data: dict, user_id: str) -> dict:
    """Insert a new analysis report using the service-role client.

    Used by the Telegram bot which has no user JWT.
    """
    client = get_supabase_client()  # service-role, bypasses RLS

    payload = {**report_data, "user_id": user_id}
    # Remove None metadata fields that shouldn't be inserted
    payload = {k: v for k, v in payload.items() if v is not None}
    response = client.table("analysis_reports").insert(payload).execute()
    return response.data[0]


def get_recent_reports_by_user(user_id: str, limit: int = 5) -> list[dict]:
    """Return the most recent reports for a user (service-role).

    Used by the Telegram bot's /history command.
    """
    client = get_supabase_client()  # service-role

    try:
        response = (
            client.table("analysis_reports")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data
    except APIError as exc:
        logger.error("Failed to fetch recent reports for user %s: %s", user_id, exc)
        return []


def save_report(report_data: dict, user_id: str, access_token: str) -> dict:
    """Insert a new analysis report and return the created row."""
    client = get_supabase_client(access_token)

    payload = {**report_data, "user_id": user_id}
    response = client.table("analysis_reports").insert(payload).execute()
    return response.data[0]


def get_reports(
    user_id: str,
    access_token: str,
    page: int = 1,
    per_page: int = 20,
    sentiment: str | None = None,
    source: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    search: str | None = None,
) -> tuple[list[dict], int]:
    """Return paginated, filtered reports for the authenticated user.

    RLS ensures the user can only see their own rows (the *access_token*
    carries the user's JWT).

    Returns
    -------
    (reports, total_count)
    """
    client = get_supabase_client(access_token)

    # We need two queries: one for the data page, one for the total count.
    # Build them in parallel using the same filters.

    def _apply_filters(query):
        """Apply optional filters to a query builder."""
        if sentiment:
            query = query.eq("sentiment", sentiment)
        if source:
            query = query.eq("source", source)
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", to_date)
        if search:
            # Use PostgREST or_ filter to search across query and summary
            query = query.or_(
                f"query.ilike.%{search}%,summary.ilike.%{search}%,topic.ilike.%{search}%"
            )
        return query

    # Data query with pagination
    offset = (page - 1) * per_page
    data_query = client.table("analysis_reports").select("*")
    data_query = _apply_filters(data_query)
    data_query = data_query.order("created_at", desc=True).range(offset, offset + per_page - 1)

    try:
        data_response = data_query.execute()
    except APIError as exc:
        logger.error("Failed to fetch reports: %s", exc)
        return [], 0

    # Count query (exact count using PostgREST Prefer header)
    count_query = client.table("analysis_reports").select("*", count=CountMethod.exact)
    count_query = _apply_filters(count_query)

    try:
        count_response = count_query.execute()
        total_count = count_response.count or 0
    except APIError as exc:
        logger.error("Failed to get report count: %s", exc)
        total_count = len(data_response.data)

    return data_response.data, total_count


def get_report_by_id(
    report_id: str, user_id: str, access_token: str
) -> dict | None:
    """Fetch a single report by ID.  Returns ``None`` if not found."""
    client = get_supabase_client(access_token)

    try:
        response = (
            client.table("analysis_reports")
            .select("*")
            .eq("id", report_id)
            .maybe_single()
            .execute()
        )
        return response.data  # None when no row matches
    except APIError as exc:
        logger.error("Failed to fetch report %s: %s", report_id, exc)
        return None


def delete_report(report_id: str, user_id: str, access_token: str) -> bool:
    """Delete a report.  Returns ``True`` if a row was actually deleted."""
    client = get_supabase_client(access_token)

    try:
        response = (
            client.table("analysis_reports")
            .delete()
            .eq("id", report_id)
            .execute()
        )
        return len(response.data) > 0
    except APIError as exc:
        logger.error("Failed to delete report %s: %s", report_id, exc)
        return False


# ---------------------------------------------------------------------------
# User bindings (Telegram <-> web account)
# ---------------------------------------------------------------------------

def save_bind_code(
    user_id: str, bind_code: str, expires_at: str, access_token: str
) -> dict:
    """Persist a new bind code for the authenticated user.

    If the user already has a pending (unbound) row we upsert to avoid
    duplicates.
    """
    client = get_supabase_client(access_token)

    payload = {
        "user_id": user_id,
        "bind_code": bind_code,
        "code_expires_at": expires_at,
    }
    response = (
        client.table("user_bindings")
        .upsert(payload, on_conflict="user_id")
        .execute()
    )
    return response.data[0]


def lookup_bind_code(bind_code: str) -> dict | None:
    """Look up a bind code (server-side, no user auth required).

    Returns ``None`` if the code does not exist or has already been consumed.
    """
    client = get_supabase_client()  # service-role, bypasses RLS

    try:
        response = (
            client.table("user_bindings")
            .select("*")
            .eq("bind_code", bind_code)
            .is_("telegram_user_id", "null")  # not yet bound
            .maybe_single()
            .execute()
        )
        if response is None or response.data is None:
            return None

        # Check expiry
        expires_at = response.data.get("code_expires_at")
        if expires_at:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expiry < datetime.now(timezone.utc):
                return None  # expired

        return response.data
    except APIError as exc:
        logger.error("Failed to look up bind code %s: %s", bind_code, exc)
        return None


def complete_binding(bind_code: str, telegram_user_id: int) -> dict:
    """Mark a bind code as consumed by writing the Telegram user ID.

    Uses the service-role client because this is called from the Telegram bot
    which does not have a web-user JWT.
    """
    client = get_supabase_client()  # service-role

    response = (
        client.table("user_bindings")
        .update(
            {
                "telegram_user_id": telegram_user_id,
                "bound_at": datetime.now(timezone.utc).isoformat(),
                "bind_code": None,  # clear the code after use
                "code_expires_at": None,
            }
        )
        .eq("bind_code", bind_code)
        .execute()
    )
    return response.data[0]


def get_binding_by_telegram_id(telegram_user_id: int) -> dict | None:
    """Return the binding row for a Telegram user, or ``None``."""
    client = get_supabase_client()  # service-role

    try:
        response = (
            client.table("user_bindings")
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .maybe_single()
            .execute()
        )
        if response is None:
            return None
        return response.data
    except APIError as exc:
        logger.error(
            "Failed to look up binding for telegram_user_id %s: %s",
            telegram_user_id,
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# Digest permission helpers (C2: all sync — matching existing pattern)
# ---------------------------------------------------------------------------

def is_admin(user_id: str, access_token: str) -> bool:
    """Check if user is in admins table."""
    client = get_supabase_client(access_token)
    try:
        result = (
            client.table("admins")
            .select("id")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return result is not None
    except APIError:
        return False


def get_digest_access_status(
    user_id: str, access_token: str
) -> str:
    """Returns: 'admin' | 'approved' | 'pending' | 'rejected' | 'none'"""
    if is_admin(user_id, access_token):
        return "admin"

    client = get_supabase_client(access_token)

    # Check digest_authorized_users
    try:
        authorized = (
            client.table("digest_authorized_users")
            .select("id")
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if authorized is not None:
            return "approved"
    except APIError:
        pass

    # Check latest access request
    try:
        request = (
            client.table("digest_access_requests")
            .select("status")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if request is not None:
            return request.data["status"]  # 'pending' or 'rejected'
    except APIError:
        pass

    return "none"


def get_all_admin_emails() -> list[str]:
    """Query admins table for all admin emails (service role)."""
    client = get_supabase_client()  # service role
    try:
        result = client.table("admins").select("email").execute()
        return [row["email"] for row in result.data]
    except APIError as exc:
        logger.error("Failed to fetch admin emails: %s", exc)
        return []


def seed_admin_if_empty() -> None:
    """Bootstrap: if admins table is empty, seed with ADMIN_EMAIL. Idempotent."""
    if not settings.admin_email:
        return
    client = get_supabase_client()  # service role
    try:
        count_resp = client.table("admins").select("id", count="exact").execute()
        if (count_resp.count or 0) == 0:
            client.rpc("seed_admin", {"p_email": settings.admin_email}).execute()
            logger.info("Seeded admin: %s", settings.admin_email)
    except Exception as exc:
        logger.error("Failed to seed admin: %s", exc)


