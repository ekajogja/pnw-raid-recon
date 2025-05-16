import time # Needed for inactive_days calculation
from datetime import datetime

def has_treaty(my_alliance, target_alliance, protected_types=None):
    """
    Check if two alliances have a treaty that should prevent raiding.

    Args:
        my_alliance: Alliance data for your nation
        target_alliance: Alliance data for target nation
        protected_types: List of treaty types that prevent raiding

    Returns:
        Boolean indicating if a treaty exists
    """
    if not protected_types:
        # Default treaty types that should prevent raiding
        protected_types = ['MDP', 'MDOAP', 'ODP', 'ODOAP', 'NAP', 'PIAT', 'Protectorate']

    if not my_alliance or not target_alliance:
        return False

    # Check both alliances' treaties
    for treaty in my_alliance.get('treaties', []):
        if (treaty['alliance1_id'] == target_alliance['id'] or
            treaty['alliance2_id'] == target_alliance['id']):
            if treaty['treaty_type'] in protected_types:
                return True

    return False

def filter_beige_targets(all_nations, my_nation, args, min_score_ratio, max_score_ratio):
    """
    Filters a list of nations to find beige nations with 1 beige turn left
    based on specified criteria.

    Args:
        all_nations: List of all nations fetched from the API.
        my_nation: Data for the user's nation.
        args: An object containing filtering parameters (limit, ignore_dnr).
        min_score_ratio: Minimum target score ratio relative to user's nation score.
        max_score_ratio: Maximum target score ratio relative to user's nation score.

    Returns:
        A list of filtered beige nations.
    """
    beige_nations = []
    for nation in all_nations:
        # Filter by color, beige_turns (>3), and score ratio
        if (nation.get('color', '').lower() == 'beige' and
            nation.get('beige_turns', 0) < 7 and
            (my_nation['score'] * min_score_ratio) <= nation.get('score', 0) <= (my_nation['score'] * max_score_ratio)):

            # Filter by alliance/treaty based on ignore_dnr
            if not args.ignore_dnr:
                # If not ignoring DNR, skip if the target has an alliance,
                # my nation has an alliance, and there is a treaty between them.
                if (nation.get('alliance_id') is not None and
                    my_nation.get('alliance') is not None and
                    has_treaty(my_nation['alliance'], nation['alliance'])):
                    continue # Skip if treaty exists and not ignoring DNR

            beige_nations.append({
                'id': nation.get('id'),
                'name': nation.get('nation_name'),
                'score': nation.get('score'),
                'beige_turns': nation.get('beige_turns'), # Added beige mode turns to output
                'alliance': nation.get('alliance').get('name', 'No Alliance') if nation.get('alliance') else 'No Alliance', # Added nation color to output
                'soldiers': nation.get('soldiers'), # Added soldiers to output
                'tanks': nation.get('tanks'), # Added tanks to output
                'aircraft': nation.get('aircraft'), # Added aircraft to output
                'ships': nation.get('ships'), # Added ships to output
                'missiles': nation.get('missiles'), # Added missiles to output
                'nukes': nation.get('nukes'), # Added nukes to output
                'spies': nation.get('spies'), # Added spies to output
            })

    # Sort by beige turns ascending, then by score descending
    beige_nations.sort(key=lambda x: (x.get('beige_turns', 0), -x.get('score', 0)))

    # Apply limit
    beige_nations = beige_nations[:args.limit]

    return beige_nations
