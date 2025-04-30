from datetime import datetime, timedelta
from config import MIN_SCORE_RATIO, MAX_SCORE_RATIO, MAX_SOLDIER_RATIO, MAX_SPIES_RATIO
from pnw_api import has_treaty

def total_infra(cities):
    """Calculate the total infrastructure of all cities."""
    return sum([float(city["infrastructure"]) for city in cities])

def calculate_money_lost(wars, nation_id):
    """Calculate total money lost as a defender in wars."""
    # With simplified war data, we don't track money lost anymore
    return 0

def has_significant_loss(nation):
    """Check if a nation has significant loss history as defender."""
    # With simplified war data, we don't track loss history
    return False

def count_wars_lost(wars, nation_id):
    """Count number of wars where nation was defender and lost."""
    # With simplified war data, we don't track war history details
    return 0

def get_war_stats(nation, now):
    """Get stats about wars and check if there are any active defensive wars."""
    wars = nation.get("wars", [])
    
    # If nation has no wars at all
    if not wars:
        return False, None, 0
    
    # Check if the nation has defensive war slots available
    # In Politics & War, each nation has 3 defensive war slots
    # If defensive_wars < 3, they can still be attacked
    defensive_wars = nation.get("defensive_wars", 0)
    
    # If the nation has 3 defensive wars, they cannot be attacked
    has_active_war = (defensive_wars >= 3)
    
    # Get time since most recent war
    last_war = wars[0]  # First war is the most recent
    war_date = datetime.strptime(last_war["date"], "%Y-%m-%dT%H:%M:%S%z")
    hours_since_war = (now - war_date.replace(tzinfo=None)).total_seconds() / 3600
    
    # We're no longer tracking money lost with the simplified API data
    return has_active_war, hours_since_war, 0

def calculate_loot_value(loot):
    """Calculate loot value (just money now)."""
    if not loot:
        return 0
    return loot["money"]

def count_active_wars(wars, nation_id):
    """Count number of active wars where nation is attacker or defender."""
    # With simplified data structure, we only check turnsleft > 0
    # We don't have attid/defid anymore
    active_count = 0
    for war in wars:
        if int(war.get("turnsleft", 0)) > 0:  # Active war
            active_count += 1
    return active_count, 0  # Return count of active wars, 0 for defending

def filter_targets(nations, my_nation, min_infra=1500, max_infra=20000, 
                  min_inactive_days=2, ignore_alliance=False, max_soldier_ratio=MAX_SOLDIER_RATIO,
                  protected_treaty_types=None):
    """
    Filter nations based on raiding criteria.
    
    Parameters:
    - nations: List of nation data from API
    - my_nation: Your nation data
    - min_infra: Minimum infrastructure to target
    - max_infra: Maximum infrastructure to target
    - min_inactive_days: Minimum days of inactivity
    - ignore_alliance: Whether to include nations with alliances
    - max_soldier_ratio: Maximum ratio of target soldiers to your soldiers
    - protected_treaty_types: Treaty types that prevent raiding
    
    Returns:
    - List of nation dictionaries that match criteria, sorted by money lost
    """
    results = []
    now = datetime.utcnow()
    
    # Calculate war range
    min_score = float(my_nation["score"]) * MIN_SCORE_RATIO
    max_score = float(my_nation["score"]) * MAX_SCORE_RATIO
    
    # Calculate maximum allowed soldiers and spies
    max_soldiers = int(float(my_nation["soldiers"]) * max_soldier_ratio)
    max_spies = int(float(my_nation.get("spies", 0)) * MAX_SPIES_RATIO)

    for n in nations:
        try:
            # Skip nations in vacation mode
            if n.get("vacation_mode_turns", 0) > 0:
                continue

            # Skip nations in beige color (protected for 2 days after losing a war)
            if n.get("color", "").lower() == "beige":
                continue

            # Check war status from last war only
            has_active_war, hours_since_war, money_lost = get_war_stats(n, now)
            
            # Skip if nation has active war
            if has_active_war:
                continue
                
            # Skip if last war was too recent (less than 24h ago)
            if hours_since_war is not None and hours_since_war < 24:
                continue

            # Parse last active date
            last_active = datetime.strptime(n["last_active"], "%Y-%m-%dT%H:%M:%S%z")
            days_inactive = (now - last_active.replace(tzinfo=None)).days
            
            # Check inactivity threshold
            if days_inactive <= min_inactive_days:
                continue

            # Check alliance
            if not ignore_alliance:
                # Skip if nation has alliance
                if n["alliance_id"] != "0" and n["alliance_id"] is not None:
                    continue

            # Must be within war range
            if float(n["score"]) < min_score or float(n["score"]) > max_score:
                continue

            # Check soldier count against ratio
            if int(n.get("soldiers", 0)) > max_soldiers:
                continue

            # Check spy count against ratio
            if int(n.get("spies", 0)) > max_spies:
                continue

            # Calculate total infrastructure
            infra_total = total_infra(n["cities"])
            # Check infrastructure range
            if infra_total < min_infra or infra_total > max_infra:
                continue

            # If we get here, target meets all criteria
            alliance_name = "No Alliance"
            if n["alliance_id"] != "0" and n["alliance_id"] is not None:
                alliance_name = n.get("alliance", {}).get("name", "Has Alliance")

            results.append({
                "name": n["nation_name"],
                "id": n["id"],
                "infra": infra_total,
                "score": float(n["score"]),
                "inactive_days": days_inactive,
                "spies": int(n.get("spies", 0)),
                "soldiers": int(n.get("soldiers", 0)),
                "max_soldiers": max_soldiers,
                "alliance": alliance_name,
                "hours_since_war": hours_since_war,
                "city_count": len(n["cities"])
            })
        except Exception as e:
            continue

    # Sort by infrastructure (higher is better)
    return sorted(results, key=lambda x: x["infra"], reverse=True)
