from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
from raid import get_raid_targets, parse_args, format_money, format_hours
import sys
import os
from dotenv import load_dotenv
from config import DEBUG

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "development-key")

@app.route('/')
def index():
    """Render the main page with the form."""
    return render_template('index.html')

@app.route('/scan', methods=['GET', 'POST'])
def scan():
    """Process the form and scan for raid targets."""
    if request.method == 'GET':
        # If someone navigates directly to /scan, redirect them to the form
        return redirect(url_for('index'))
    try:
        # Create a namespace object similar to what argparse would return
        class Args:
            pass
        
        args = Args()
        
        try:
            # Set default values
            args.min_infra = int(request.form.get('min_infra', 2500))
            args.max_infra = int(request.form.get('max_infra', 20000))
            args.inactive_time = float(request.form.get('inactive_time', 1.5))
            args.ignore_dnr = request.form.get('ignore_dnr') == 'true'
            args.troop_ratio = float(request.form.get('troop_ratio', 0.1))
            args.limit = int(request.form.get('limit', 10))
        except (ValueError, TypeError) as e:
            flash(f"Invalid form data: {str(e)}", "error")
            return redirect(url_for('index'))
        
        try:
            # Get raid targets
            my_nation, targets = get_raid_targets(args)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in get_raid_targets: {str(e)}\n{error_details}")
            flash(f"Error getting targets: {str(e)}", "error")
            return redirect(url_for('index'))
        
        # Calculate summary statistics
        total_infra = sum(t['infra'] for t in targets) if targets else 0
        total_money_lost = sum(t.get('money_lost', 0) for t in targets) if targets else 0
        nations_with_losses = sum(1 for t in targets if t.get('money_lost', 0) > 0) if targets else 0
        
        # Print summary and results to console for command-line viewing
        print("\n📊 Summary:")
        print(f"  Found {len(targets)} potential raid targets")
        print(f"  Total target infrastructure: {total_infra:,.2f}")
        if targets:
            print(f"  Average infra per target: {total_infra/len(targets):,.2f}")
        else:
            print("  No targets found")
        print(f"  Nations with previous losses: {nations_with_losses}/{len(targets) if targets else 0}")
        print(f"  Total money lost across targets: {format_money(total_money_lost)}")
        
        print(f"\n🎯 Top {len(targets)} Raid Targets (sorted by money lost):")
        for i, t in enumerate(targets, 1):
            nation_url = f"https://politicsandwar.com/nation/id={t['id']}"
            print(f"{i}. {t['name']} (ID: {t['id']}) | {t['alliance']}")
            print(f"  Score: {t['score']:,.2f} | Infra: {t['infra']:,.2f} | Cities: {t.get('city_count', '?')}")
            print(f"  Intel: {t['spies']} spies | Troops: {t['soldiers']:,}/{t['max_soldiers']:,}")
            print(f"  Inactive: {t['inactive_days']}d | Last war: {format_hours(t.get('hours_since_war'))} ago")
            print(f"  Money lost in wars: {format_money(t.get('money_lost', 0))}")
            print(f"  URL: {nation_url}")
            print(f"  Attack: https://politicsandwar.com/nation/war/declare/id={t['id']}")
            print()
        
        # Prepare data for template
        data = {
            'my_nation': my_nation,
            'targets': targets if targets else [],  # Ensure targets is never None
            'params': {
                'min_infra': args.min_infra,
                'max_infra': args.max_infra,
                'inactive_time': args.inactive_time,
                'ignore_dnr': args.ignore_dnr,
                'troop_ratio': args.troop_ratio,
                'limit': args.limit
            }
        }
        
        # Helper functions for templates - pass as separate arguments to avoid string formatting issues
        return render_template('results.html', data=data, 
                              format_money=format_money, 
                              format_hours=format_hours)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Unhandled error in scan route: {str(e)}\n{error_details}")
        flash(f"An unexpected error occurred: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/api/scan', methods=['POST'])
def api_scan():
    """API endpoint to get raid targets as JSON."""
    try:
        # Create a namespace object similar to what argparse would return
        class Args:
            pass
        
        args = Args()
        
        # Parse the request JSON
        req_data = request.get_json() or {}
        
        try:
            # Set default values
            args.min_infra = int(req_data.get('min_infra', 2500))
            args.max_infra = int(req_data.get('max_infra', 20000))
            args.inactive_time = float(req_data.get('inactive_time', 1.5))
            args.ignore_dnr = req_data.get('ignore_dnr', False)
            args.troop_ratio = float(req_data.get('troop_ratio', 0.1))
            args.limit = int(req_data.get('limit', 10))
        except (ValueError, TypeError) as e:
            return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
        
        try:
            # Get raid targets
            my_nation, targets = get_raid_targets(args)
            
            # Print results to console for command-line viewing
            print(f"\n🎯 Top {len(targets)} Raid Targets from API (sorted by money lost):")
            for t in targets:
                nation_url = f"https://politicsandwar.com/nation/id={t['id']}"
                print(f"- {t['name']} (ID: {t['id']}) | {t['alliance']}")
                print(f"  Score: {t['score']:,.2f} | Infra: {t['infra']:,.2f}")
                print(f"  Intel: {t['spies']} spies | Troops: {t['soldiers']:,}/{t['max_soldiers']:,}")
                print(f"  Inactive: {t['inactive_days']}d | Last war: {format_hours(t.get('hours_since_war'))} ago")
                print(f"  Money lost in wars: {format_money(t.get('money_lost', 0))}")
                print(f"  URL: {nation_url}")
                print()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in API get_raid_targets: {str(e)}\n{error_details}")
            return jsonify({'error': str(e)}), 500
        
        return jsonify({
            'my_nation': my_nation,
            'targets': targets,
            'params': {
                'min_infra': args.min_infra,
                'max_infra': args.max_infra,
                'inactive_time': args.inactive_time,
                'ignore_dnr': args.ignore_dnr,
                'troop_ratio': args.troop_ratio,
                'limit': args.limit
            }
        })
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Unhandled error in API scan route: {str(e)}\n{error_details}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
