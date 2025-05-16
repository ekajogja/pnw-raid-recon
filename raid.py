from pnw_api import get_my_nation, get_nations, has_treaty
from tqdm import tqdm
import traceback
import argparse
import os
import time
from datetime import datetime
from config import IGNORE_DNR, MAX_PAGES, MIN_SCORE_RATIO, MAX_SCORE_RATIO

def get_last_updated():
    try:
        import subprocess
        result = subprocess.run(['git', 'log', '-1', '--format=%cd', '--date=short'],
                              capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")  # Fallback to current date

def parse_args():
    parser = argparse.ArgumentParser(description='PnW Raid Recon - Find optimal raiding targets')
    parser.add_argument('--ignore-dnr', action='store_true', default=IGNORE_DNR,
                      help='Show nations in alliances but still respect treaties (default: False)')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of results (default: 10)')
    parser.add_argument('--max-pages', type=int, default=MAX_PAGES,
                      help=f'Maximum number of pages to fetch (default: {MAX_PAGES}, use smaller number for testing)')
    parser.add_argument('--min-inactive-days', type=int, default=2,
                      help='Minimum number of inactive days (default: 2)')
    return parser.parse_args()

def format_param_info(name, value, description=None):
    if description:
        return f"  {name}: {value} - {description}"
    return f"  {name}: {value}"

def format_money(amount):
    if amount >= 1000000000:
        return f"${amount/1000000000:.1f}B"
    if amount >= 1000000:
        return f"${amount/1000000:.1f}M"
    return f"${amount:,.0f}"

def format_hours(hours):
    if hours is None:
        return "no previous wars"
    return f"{int(hours)}h" if hours < 48 else f"{int(hours/24)}d {int(hours%24)}h"

def format_loot(loot, loot_value=None):
    if not loot:
        return "No loss data"
    if loot["money"] > 0:
        return f"Lost ${loot['money']:,.0f}"
    return "No losses"

def get_raid_targets(api_key, args):
    # Get my nation's info first
    my_nation = get_my_nation(api_key)

    # Display all parameters and their meanings
    print("Current Parameters:")
    print(format_param_info(
        "War Range",
        f"{MIN_SCORE_RATIO*100:.0f}% - {MAX_SCORE_RATIO*100:.0f}%",
        f"Based on your score: {float(my_nation['score']):,.2f}"
    ))
    print(format_param_info(
        "DNR Filter",
        "Including Allied Nations" if args.ignore_dnr else "Respecting DNR"
    ))

    # Show alliance info if we have one
    if my_nation.get("alliance"):
        print(format_param_info(
            "Your Alliance",
            my_nation["alliance"]["name"]
        ))

    print("")  # Add a blank line for readability

    page = 1
    all_nations = []
    filtered = []

    pbar = tqdm(desc="Fetching nations", unit="page")

    while True:
        try:
            print(f"Fetching page {page}...")
            nations_data = get_nations(api_key, page)

            if not nations_data["data"]:  # No more nations to fetch
                break

            # Process just the current page of nations
            current_page_nations = nations_data["data"]
            all_nations.extend(current_page_nations)
            pbar.update(1)

            # Process nations on the current page and apply filtering
            for nation in current_page_nations:
                # Find the last bank record matching the criteria
                last_alliance_bank_rec = None
                # Check if bankrecs exists and is a list
                if nation.get('bankrecs') and nation.get('alliance') and isinstance(nation['bankrecs'], list):
                    for rec in nation['bankrecs']:
                        if (rec.get('sender') and rec['sender'].get('id') == nation['id'] and
                            rec.get('receiver') and rec['receiver'].get('id') == nation['alliance']['id'] and
                            rec.get('money', 0) >= 1000000):
                            last_alliance_bank_rec = rec
                            break # Found the most recent one due to orderBy DESC in query in API call

                # Add bank record info to the nation data
                nation['last_alliance_bank_rec'] = last_alliance_bank_rec

                # Calculate total money stolen from the most recent defensive war
                total_money_stolen_recent_def_war = 0
                most_recent_def_war_date = None
                # Add checks for defensive_wars and the date field
                if nation.get('defensive_wars') and isinstance(nation['defensive_wars'], list) and len(nation['defensive_wars']) > 0:
                    most_recent_def_war = nation['defensive_wars'][0]
                    if isinstance(most_recent_def_war, dict) and most_recent_def_war.get('date'):
                        most_recent_def_war_date = datetime.strptime(most_recent_def_war['date'], '%Y-%m-%dT%H:%M:%S%z')
                        if most_recent_def_war.get('attacks'):
                            for attack in most_recent_def_war['attacks']:
                                total_money_stolen_recent_def_war += attack.get('money_stolen', 0)

                # Add money stolen info to the nation data
                nation['money_stolen_recent_def_war'] = total_money_stolen_recent_def_war

                # Implement the new filtering logic
                include_nation = True # Assume nation is included unless filtered out

                # 1. Initial State Filter (War Range, Vacation, Beige, Inactive)
                nation_score = nation.get('score', 0)
                min_score = my_nation['score'] * MIN_SCORE_RATIO
                max_score = my_nation['score'] * MAX_SCORE_RATIO

                if not (min_score <= nation_score <= max_score):
                    include_nation = False

                if include_nation and nation.get('vacation_mode_turns', 0) > 0:
                    include_nation = False

                if include_nation and nation.get('color') == 'Beige':
                    include_nation = False

                # Calculate inactive days
                inactive_days = None
                if nation.get('last_active'):
                    try:
                        last_active_timestamp = datetime.strptime(nation['last_active'], '%Y-%m-%d %H:%M:%S').timestamp()
                        inactive_days = (time.time() - last_active_timestamp) / (60 * 60 * 24)
                    except ValueError:
                        # Handle potential date format issues
                        pass

                if include_nation and inactive_days is not None and inactive_days < args.min_inactive_days:
                    include_nation = False

                # 2. DNR Filter
                if include_nation and not args.ignore_dnr:
                    if (nation.get('alliance_id') is not None and
                        my_nation.get('alliance') is not None and
                        nation.get('alliance') is not None and # Ensure target nation has alliance data
                        has_treaty(my_nation['alliance'], nation['alliance'])):
                        include_nation = False

                # Add money stolen filter back with a threshold of 50,000
                if include_nation and total_money_stolen_recent_def_war < 50000:
                    include_nation = False

                if include_nation:
                    # Add relevant data to the filtered nation dictionary
                    filtered_nation_data = {
                        'id': nation.get('id'),
                        'name': nation.get('nation_name'),
                        'score': nation.get('score'),
                        'alliance': nation.get('alliance').get('name', 'No Alliance') if nation.get('alliance') else 'No Alliance',
                        'money_stolen_recent_def_war': total_money_stolen_recent_def_war,
                        'most_recent_def_war_date': most_recent_def_war_date.strftime('%Y-%m-%d %H:%M:%S%z') if most_recent_def_war_date else 'N/A',
                        # Add other fields needed for output here
                        'city_count': nation.get('city_count', '?'),
                        'last_alliance_bank_rec': nation.get('last_alliance_bank_rec') # Keep this for now if needed elsewhere
                    }
                    filtered.append(filtered_nation_data)

            # Limit to the requested number of targets
            if len(filtered) >= args.limit:
                print(f"\nFound {len(filtered)} targets, stopping search")
                break

            # Check if we should continue to next page
            paginator = nations_data.get("paginatorInfo", {})
            if not paginator.get("hasMorePages") or page >= args.max_pages:  # Stop at max pages
                print(f"\nReached page limit ({page}/{args.max_pages})")
                break

            page += 1
        except Exception as e:
            print(f"\n❌ Error fetching page {page}: {str(e)}")
            traceback.print_exc()

            # If we already have some nations, just use what we have
            if all_nations:
                print(f"\n✅ Using {len(all_nations)} nations already fetched before error")
                break
            else:
                # No nations fetched yet, try one more time with a delay
                try:
                    print("Retrying with a 5-second delay...")
                    time.sleep(5)
                    nations_data = get_nations(api_key, page)
                    all_nations.extend(nations_data["data"])
                    pbar.update(1)
                    page += 1
                except Exception as retry_e:
                    print(f"\n❌ Retry also failed: {str(retry_e)}")
                    # Terminate with an error if we can't fetch any data
                    if not all_nations:
                        raise ValueError("Could not fetch any nation data from API after retries")
                    break

    pbar.close()

    return my_nation, filtered

def main():
    try:
        args = parse_args()
        print("[⚔️] Samurai Raid Scanner - Finding optimal targets...\n")

        # For CLI usage, the API key still needs to come from the environment
        # This part of the code is for the CLI, not the web interface
        api_key = os.getenv("PNW_API_KEY")
        if not api_key:
             raise ValueError("PNW_API_KEY environment variable is not set for CLI usage.")

        my_nation, filtered = get_raid_targets(api_key, args)

        if args.json:
            import json
            print(json.dumps(filtered, indent=2))
            return

        # Print summary first
        print("\n📊 Summary:")
        print(f"  Found {len(filtered)} potential raid targets")

        # Print detailed target information
        print(f"\n🎯 Top {len(filtered)} Raid Targets:")
        for i, t in enumerate(filtered, 1):
            nation_url = f"https://politicsandwar.com/nation/id={t['id']}"
            print(f"{i}. {t['name']} (ID: {t['id']}) | {t['alliance']}")
            print(f"  Score: {t['score']:,.2f} | Cities: {t.get('city_count', '?')}")

            # Print bank record info
            if t.get('last_alliance_bank_rec'):
                print(f"  Last Alliance Bank Rec: {format_money(t['last_alliance_bank_rec']['money'])} on {t['last_alliance_bank_rec']['date']}")
            else:
                print("  Last Alliance Bank Rec: N/A")

            # Print money stolen info in the requested format
            money_stolen_amount = format_money(t.get('money_stolen_recent_def_war', 0))
            money_stolen_date = t.get('most_recent_def_war_date', 'N/A')
            print(f"  last money stolen: {money_stolen_amount} / {money_stolen_date}")

            # Print last alliance bank transaction info
            if t.get('last_alliance_bank_rec'):
                bank_rec_amount = format_money(t['last_alliance_bank_rec']['money'])
                bank_rec_date = t['last_alliance_bank_rec']['date']
                print(f"  last alliance bank transaction: {bank_rec_amount} / {bank_rec_date}")
            else:
                print("  last alliance bank transaction: N/A")

            print(f"  URL: {nation_url}")
            print(f"  Attack: https://politicsandwar.com/nation/war/declare/id={t['id']}")
            print()

        # Print usage tips - Keep relevant ones, remove infra/troop ratio/inactive time
        print("\nRaid Options:")
        print("  --ignore-dnr         Show nations in alliances (respects treaties) (current: {})".format(args.ignore_dnr))
        print("  --json               Output results in JSON format")
        print("  --limit N            Limit number of results (current: {})".format(args.limit))
        print("  --max-pages N        Maximum number of pages to fetch (current: {})".format(args.max_pages))


        # Print footer
        print("\n" + "=" * 80)
        print(f"Samurai Raid Scanner - last updated {get_last_updated()}")
        print("For optimal raiding results and to avoid counters, respect DNR lists and alliance treaties")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
