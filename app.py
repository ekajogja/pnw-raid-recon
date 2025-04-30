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

@app.route('/scan', methods=['POST'])
def scan():
    """Process the form and scan for raid targets."""
    try:
        # Create a namespace object similar to what argparse would return
        class Args:
            pass
        
        args = Args()
        
        # Set default values
        args.min_infra = int(request.form.get('min_infra', 2500))
        args.max_infra = int(request.form.get('max_infra', 20000))
        args.inactive_time = float(request.form.get('inactive_time', 1.5))
        args.ignore_dnr = request.form.get('ignore_dnr') == 'true'
        args.troop_ratio = float(request.form.get('troop_ratio', 0.1))
        args.limit = int(request.form.get('limit', 10))
        
        # Get raid targets
        my_nation, targets = get_raid_targets(args)
        
        # Prepare data for template
        data = {
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
        }
        
        # Helper functions for templates
        data['format_money'] = format_money
        data['format_hours'] = format_hours
        
        return render_template('results.html', data=data)
    
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
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
        
        # Set default values
        args.min_infra = int(req_data.get('min_infra', 2500))
        args.max_infra = int(req_data.get('max_infra', 20000))
        args.inactive_time = float(req_data.get('inactive_time', 1.5))
        args.ignore_dnr = req_data.get('ignore_dnr', False)
        args.troop_ratio = float(req_data.get('troop_ratio', 0.1))
        args.limit = int(req_data.get('limit', 10))
        
        # Get raid targets
        my_nation, targets = get_raid_targets(args)
        
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
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)
