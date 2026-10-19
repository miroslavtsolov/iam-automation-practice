import pandas as pd
from fetch_users import fetch_all_users
from logger import get_logger

log = get_logger()

def reconcile():
    log.info("Starting access review reconciliation")

    kc_users = fetch_all_users()
    kc_df = pd.DataFrame([{
        "username": u.get("username"),
        "email": u.get("email"),
        "enabled": u.get("enabled"),
    } for u in kc_users])

    hr_df = pd.read_csv("hr_feed.csv")

    # Email is the correlation key. pandas would otherwise match blank (NaN)
    # emails to each other, duplicating rows and hiding real orphans, so
    # accounts without an email (e.g. service accounts) are set aside for
    # manual review instead of being reconciled.
    no_email = kc_df[kc_df["email"].isna() | (kc_df["email"].astype(str).str.strip() == "")]
    if len(no_email):
        log.warning(
            f"{len(no_email)} account(s) have no email and were skipped, review manually: "
            + ", ".join(no_email["username"].astype(str))
        )
    kc_df = kc_df.drop(no_email.index)
    hr_df = hr_df.dropna(subset=["email"])

    merged = kc_df.merge(hr_df, left_on="email", right_on="email", how="left", indicator=True)

    orphaned = merged[merged["_merge"] == "left_only"]  # in Keycloak, not in HR feed
    terminated_but_enabled = merged[(merged["status"] == "terminated") & (merged["enabled"] == True)]

    log.info(f"Total Keycloak users: {len(kc_df)}")
    log.info(f"Orphaned accounts found: {len(orphaned)}")
    log.info(f"Terminated-but-still-enabled accounts found: {len(terminated_but_enabled)}")

    return merged, orphaned, terminated_but_enabled
