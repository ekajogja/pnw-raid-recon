from pnw_api import get_my_nation, get_nations
from filter import filter_targets
from tqdm import tqdm
import traceback
import argparse
import os
import time
from datetime import datetime
from config import MIN_INFRA, MAX_INFRA, MIN_INACTIVE_DAYS, IGNORE_DNR, MAX_PAGES, MIN_SCORE_RATIO, MAX_SCORE_RATIO, MAX_SOLDIER_RATIO

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
    parser.add_argument('--min-infra', type=int, default=MIN_INFRA,
                      help=f'Minimum target infra (default: {MIN_INFRA:,})')
    parser.add_argument('--max-infra', type=int, default=MAX_INFRA,
                      help=f'Maximum target infra (default: {MAX_INFRA:,})')
    parser.add_argument('--inactive-time', type=float, default=MIN_INACTIVE_DAYS,
                      help=f'Minimum inactive time in days (default: {MIN_INACTIVE_DAYS} days / {MIN_INACTIVE_DAYS*24:.0f}h)')
    parser.add_argument('--ignore-dnr', action='store_true', default=IGNORE_DNR,
                      help='Show nations in alliances but still respect treaties (default: False)')
    parser.add_argument('--troop-ratio', type=float, default=MAX_SOLDIER_RATIO,
                      help=f'Maximum enemy/friendly troop ratio (default: {MAX_SOLDIER_RATIO})')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of results (default: 10)')
    parser.add_argument('--max-pages', type=int, default=MAX_PAGES, 
                      help=f'Maximum number of pages to fetch (default: {MAX_PAGES}, use smaller number for testing)')
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

def get_raid_targets(args):
    # Get my nation's info first
    my_nation = get_my_nation()
    max_soldiers = int(float(my_nation["soldiers"]) * args.troop_ratio)
    
    # Display all parameters and their meanings
    print("Current Parameters:")
    print(format_param_info(
        "Infra Range", 
        f"{args.min_infra:,} - {args.max_infra:,}"
    ))
    print(format_param_info(
        "War Range", 
        f"{MIN_SCORE_RATIO*100:.0f}% - {MAX_SCORE_RATIO*100:.0f}%",
        f"Based on your score: {float(my_nation['score']):,.2f}"
    ))
    print(format_param_info(
        "Troop Limit",
        f"{max_soldiers:,} ({args.troop_ratio*100:.0f}% of your {int(my_nation['soldiers']):,})"
    ))
    print(format_param_info(
        "Inactive Time",
        f"{args.inactive_time:.1f}d ({args.inactive_time*24:.0f}h)"
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
            nations_data = get_nations(page)
            
            if not nations_data["data"]:  # No more nations to fetch
                break
                
            # Process just the current page of nations
            current_page_nations = nations_data["data"]
            all_nations.extend(current_page_nations)
            pbar.update(1)
            
            # Filter just the current page nations (faster)
            new_targets = filter_targets(
                current_page_nations,
                my_nation,
                min_infra=args.min_infra,
                max_infra=args.max_infra,
                min_inactive_days=args.inactive_time,
                ignore_alliance=args.ignore_dnr,
                max_soldier_ratio=args.troop_ratio
            )
            
            # Add new targets to our filtered list
            filtered.extend(new_targets)
            
            # Sort by infrastructure (highest first)
            filtered = sorted(filtered, key=lambda x: x["infra"], reverse=True)
            
            # Limit to the requested number of targets
            if len(filtered) >= args.limit:
                filtered = filtered[:args.limit]
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
                    nations_data = get_nations(page)
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
        print("[🏴‍☠️] PnW Raid Recon - Finding optimal targets...\n")
        
        my_nation, filtered = get_raid_targets(args)
        
        if args.json:
            import json
            print(json.dumps(filtered, indent=2))
            return
        
        # Print summary first
        total_infra = sum(t['infra'] for t in filtered)
        
        print("\n📊 Summary:")
        print(f"  Found {len(filtered)} potential raid targets")
        print(f"  Total target infrastructure: {total_infra:,.2f}")
        print(f"  Average infra per target: {total_infra/len(filtered):,.2f}" if filtered else "  No targets found")
        
        # Print detailed target information
        print(f"\n🎯 Top {len(filtered)} Raid Targets (sorted by infrastructure):")
        for i, t in enumerate(filtered, 1):
            nation_url = f"https://politicsandwar.com/nation/id={t['id']}"
            print(f"{i}. {t['name']} (ID: {t['id']}) | {t['alliance']}")
            print(f"  Score: {t['score']:,.2f} | Infra: {t['infra']:,.2f} | Cities: {t.get('city_count', '?')}")
            print(f"  Intel: {t['spies']} spies | Troops: {t['soldiers']:,}/{t['max_soldiers']:,}")
            print(f"  Inactive: {t['inactive_days']}d | Last war: {format_hours(t.get('hours_since_war'))} ago")
            print(f"  URL: {nation_url}")
            print(f"  Attack: https://politicsandwar.com/nation/war/declare/id={t['id']}")
            print()

        # Print usage tips
        print("\nRaid Options:")
        print("  --min-infra N        Set minimum target infra (current: {:,})".format(args.min_infra))
        print("  --max-infra N        Set maximum target infra (current: {:,})".format(args.max_infra))
        print("  --inactive-time N    Set minimum inactive time in days (current: {:.1f}d)".format(args.inactive_time))
        print("  --troop-ratio N      Set maximum enemy/friendly troop ratio (current: {:.1%})".format(args.troop_ratio))
        print("  --ignore-dnr         Show nations in alliances (respects treaties) (current: {})".format(args.ignore_dnr))
        print("  --json               Output results in JSON format")
        print("  --limit N            Limit number of results (current: {})".format(args.limit))

        # Print footer
        print("\n" + "=" * 80)
        print(f"PnW Raid Recon - last updated {get_last_updated()}")
        print("For optimal raiding results and to avoid counters, respect DNR lists and alliance treaties")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
