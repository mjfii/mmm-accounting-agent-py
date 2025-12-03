"""
Download Zoho Books Chart of Accounts via API.

Required environment variables:
    ZOHO_BOOKS_ORG_ID       -> Your Zoho Books organization ID
    ZOHO_BOOKS_ACCESS_TOKEN -> OAuth access token with ZohoBooks.accountants.READ

Optional:
    ZOHO_BOOKS_API_DOMAIN   -> Base API domain, default: https://www.zohoapis.com
                               (Use https://www.zohoapis.eu, .in, etc. for other DCs.)
"""

import os
import sys
import requests

ORG_ID = '872456762' # os.environ.get("ZOHO_BOOKS_ORG_ID")
ACCESS_TOKEN = '' # os.environ.get("ZOHO_BOOKS_ACCESS_TOKEN")
API_DOMAIN = "https://www.zohoapis.com"

if not ORG_ID or not ACCESS_TOKEN:
    raise SystemExit("ZOHO_BOOKS_ORG_ID and ZOHO_BOOKS_ACCESS_TOKEN must be set")

def fetch_chart_of_accounts(
    show_balance: bool = False,
    filter_by: str | None = None,
    per_page: int = 200,
) -> list[dict]:
    headers = {
        "Authorization": f"Zoho-oauthtoken {ACCESS_TOKEN}",
    }

    all_accounts: list[dict] = []
    page = 1

    while True:
        params: dict[str, str | int] = {
            "organization_id": ORG_ID,
            "page": page,
            "per_page": per_page,
        }
        if show_balance:
            params["showbalance"] = "true"
        if filter_by:
            params["filter_by"] = filter_by

        url = f"{API_DOMAIN}/books/v3/chartofaccounts"
        resp = requests.get(url, headers=headers, params=params, timeout=30)

        if resp.status_code != 200:
            raise SystemExit(
                f"API request failed (status {resp.status_code}): {resp.text}"
            )

        data = resp.json()
        accounts = (
            data.get("chartofaccounts")
            or data.get("chart_of_accounts")
            or []
        )

        if not accounts:
            break

        all_accounts.extend(accounts)

        page_context = data.get("page_context") or {}
        has_more = page_context.get("has_more_page")
        if has_more is True:
            page += 1
        else:
            if len(accounts) < per_page:
                break
            page += 1

    return all_accounts