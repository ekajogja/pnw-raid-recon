from pnw_api import get_beige_nations
import sys
import os
from dotenv import load_dotenv
import argparse # Import argparse
import traceback # Import traceback
from config import MIN_INACTIVE_DAYS, IGNORE_DNR, MAX_PAGES, MIN_SCORE_RATIO, MAX_SCORE_RATIO, MAX_SOLDIER_RATIO # Import constants from config
from datetime import datetime # Import datetime for date formatting

# Load environment variables
load_dotenv()

def format_money(amount):
    if amount is None:
        return "$0"
    if amount >= 1000000000:
        return f"${amount/1000000000:.1f}B"
    if amount >= 1000000:
        return f"${amount/1000000:.1f}M"
    return f"${amount:,.0f}"

def format_hours(hours):
    if hours is None:
        return "no previous wars"
    return f"{int(hours)}h" if hours < 48 else f"{int(hours/24)}d {int(hours%24)}h"

def get_last_updated():
    try:
        import subprocess
        result = subprocess.run(['git', 'log', '-1', '--format=%cd', '--date=short'],
                              capture_output=True, text=True)
        return result.stdout.strip()
    except Exception:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")  # Fallback to current date

def format_param_info(name, value, description=None):
    if description:
        return f"  {name}: {value} - {description}"
    return f"  {name}: {value}"

def main():
    parser = argparse.ArgumentParser(description='PnW Beige Finder - Find nations with 1 beige turn left')
    parser.add_argument('--api-key', type=str, help='Your Politics & War API key')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of results (default: 10)')
    parser.add_argument('--max-pages', type=int, default=MAX_PAGES,
                      help=f'Maximum number of pages to fetch (default: {MAX_PAGES}, use smaller number for testing)')
    parser.add_argument('--ignore-dnr', action='store_true', default=False,
                      help='Ignore alliance treaties and show all nations (default: False, respects treaties)')
    parser.add_argument('--min-score-ratio', type=float, default=MIN_SCORE_RATIO,
                      help=f'Minimum target score ratio (default: {MIN_SCORE_RATIO})')
    parser.add_argument('--max-score-ratio', type=float, default=MAX_SCORE_RATIO,
                      help=f'Maximum target score ratio (default: {MAX_SCORE_RATIO})')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')

    args = parser.parse_args()

    print("[🔎] Samurai Beige Finder - Finding beige nations...\n")

    api_key = args.api_key or os.getenv("PNW_API_KEY")
    if not api_key:
         raise ValueError("PNW_API_KEY environment variable or --api-key argument is not set for CLI usage.")

    try:
        # Get my nation's info first (needed for score ratio description)
        # Assuming get_my_nation is available in pnw_api
        from pnw_api import get_my_nation
        my_nation = get_my_nation(api_key)

        # Display all parameters and their meanings
        print("Current Parameters:")
        print(format_param_info(
            "Score Ratio Range",
            f"{args.min_score_ratio*100:.0f}% - {args.max_score_ratio*100:.0f}%",
            f"Based on your score: {float(my_nation['score']):,.2f}"
        ))
        print(format_param_info(
            "DNR Filter",
            "Including Allied Nations" if args.ignore_dnr else "Respecting DNR"
        ))
        print(format_param_info(
            "Max Pages",
            f"{args.max_pages}"
        ))

        # Show alliance info if we have one
        if my_nation.get("alliance"):
            print(format_param_info(
                "Your Alliance",
                my_nation["alliance"]["name"]
            ))

        print("")  # Add a blank line for readability

        # Pass score ratio arguments to get_beige_nations
        my_nation, filtered = get_beige_nations(api_key, args, args.min_score_ratio, args.max_score_ratio)

        if args.json:
            import json
            print(json.dumps(filtered, indent=2))
            return

        # Print summary first
        print("\n📊 Summary:")
        print(f"  Found {len(filtered)} potential beige nations")
        print("  No targets found" if not filtered else "")

        # Print detailed target information
        print(f"\n🎯 Top {len(filtered)} Beige Nations (sorted by score):")
        for i, t in enumerate(filtered, 1):
            nation_url = f"https://politicsandwarwar.com/nation/id={t['id']}"
            print(f"{i}. {t['name']} | {t['alliance']}")
            print(f"  Score: {t['score']:,.2f} | Beige Turns: {t.get('beige_turns', '?')}") # Print score and beige turns on one line
            print(f"  Military: 🧍{t.get('soldiers', '?')}  टैंक{t.get('tanks', '?')} ✈️{t.get('aircraft', '?')} 🚢{t.get('ships', '?')} 🚀{t.get('missiles', '?')} ☢️{t.get('nukes', '?')} 🕵️{t.get('spies', '?')}") # Print military units with emojis
            print(f"  URL: https://politicsandwarwar.com/nation/id={t['id']}")
            print()

        # Print usage tips
        print("\nBeige Finder Options:")
        # print(format_param_info("--api-key API_KEY", "Your Politics & War API key")) # Removed --api-key tip
        print(format_param_info("--ignore-dnr", "Show nations in alliances (respects treaties)", f"current: {args.ignore_dnr}"))
        # print(format_param_info("--json", "Output results in JSON format")) # Removed --json tip
        print(format_param_info("--limit N", "Limit number of results", f"current: {args.limit}"))
        print(format_param_info("--max-pages N", "Maximum number of pages to fetch", f"current: {args.max_pages}"))


        # Print footer
        print("\n" + "=" * 80)
        print(f"Samurai Beige Finder - last updated {get_last_updated()}")
        print("For optimal raiding results and to avoid counters, respect DNR lists and alliance treaties")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
