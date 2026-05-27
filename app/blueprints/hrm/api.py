from flask import request, jsonify
from flask_login import login_required, current_user
import datetime
from app.blueprints.hrm import hrm_bp
from app.blueprints.hrm.services import calculate_suggested_payroll, log_attendance
from app.blueprints.hrm.permissions import hrm_management_required

@hrm_bp.route('/api/payroll/preview', methods=['GET'])
@login_required
@hrm_management_required
def api_payroll_preview():
    """
    Returns aggregated attendance data and suggested payroll calculations for staff.
    """
    user_id = request.args.get('user_id')
    month = request.args.get('month')
    year = request.args.get('year')
    
    if not user_id or not month or not year:
        return jsonify({'error': 'Missing user_id, month, or year parameters.'}), 400
        
    try:
        month = int(month)
        year = int(year)
    except ValueError:
        return jsonify({'error': 'Month and year must be valid integers.'}), 400
        
    try:
        preview_data = calculate_suggested_payroll(
            organization_id=current_user.organization_id,
            user_id=user_id,
            month=month,
            year=year
        )
        return jsonify(preview_data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hrm_bp.route('/api/attendance/quick', methods=['POST'])
@login_required
@hrm_management_required
def api_quick_attendance():
    """
    Processes quick daily attendance logging from roster matrix interface.
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')
    status = data.get('status')
    date_str = data.get('date')
    
    if not user_id or not status:
        return jsonify({'error': 'Missing user_id or status.'}), 400
        
    try:
        if date_str:
            target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = datetime.date.today()
    except ValueError:
        return jsonify({'error': 'Invalid date format (must be YYYY-MM-DD).'}), 400
        
    try:
        record = log_attendance(
            organization_id=current_user.organization_id,
            user_id=user_id,
            date=target_date,
            status=status
        )
        return jsonify({
            'message': 'Attendance successfully logged.',
            'user_id': user_id,
            'status': record.status,
            'date': record.date.strftime('%Y-%m-%d')
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An internal error occurred: ' + str(e)}), 500
