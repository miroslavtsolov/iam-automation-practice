import argparse
import pandas as pd
from reconcile import reconcile
from fetch_users import fetch_all_users, disable_user
from logger import get_logger

log = get_logger()

def pd_concat_unique(*dfs):
    return pd.concat(dfs).drop_duplicates(subset="email")

def remediate(dry_run=True):
    merged, orphaned, terminated_but_enabled = reconcile()
    to_disable = pd_concat_unique(orphaned, terminated_but_enabled)

    kc_users = fetch_all_users()
    email_to_id = {u.get("email"): u.get("id") for u in kc_users}

    for _, row in to_disable.iterrows():
        email = row["email"]
        user_id = email_to_id.get(email)
        if not user_id:
            log.warning(f"Could not resolve Keycloak id for {email}, skipping")
            continue

        if dry_run:
            log.info(f"[DRY RUN] Would disable user: {row['username']} ({email})")
        else:
            disable_user(user_id)
            log.info(f"DISABLED user: {row['username']} ({email})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Disable orphaned / terminated-but-enabled accounts")
    parser.add_argument("--dry-run", action="store_true", help="Log what would happen without making changes")
    parser.add_argument("--confirm", action="store_true", help="Required alongside omitting --dry-run to actually disable accounts")
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("Refusing to make live changes without --confirm. Use --dry-run to preview instead.")
    else:
        remediate(dry_run=args.dry_run)
