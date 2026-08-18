from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db, WorkOrder, User, WorkOrderStatus
from datetime import datetime, timezone

schedule_bp = Blueprint('schedule', __name__, template_folder='templates/schedule')

@schedule_bp.route('/')
@login_required
def index():
    if current_user.role not in ['Admin', 'Supervisor']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    from models import Site
    if current_user.site_id:
        sites = Site.query.filter_by(id=current_user.site_id).all()
    else:
        sites = Site.query.all()
            
    return render_template('schedule/index.html', sites=sites)

@schedule_bp.route('/site/<int:site_id>')
@login_required
def site_schedule(site_id):
    if current_user.role not in ['Admin', 'Supervisor']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
        
    from models import Site, Shift, UserShift, Team
    site = Site.query.get_or_404(site_id)
    
    # Ensure supervisor can only see their site
    if current_user.role != 'Admin' and current_user.site_id and current_user.site_id != site.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('schedule.index'))
    technicians = User.query.filter(User.role != 'Admin', User.site_id == site.id).all()
    teams = Team.query.filter_by(site_id=site.id).all()
    
    return render_template('schedule/site_schedule.html', site=site, technicians=technicians, teams=teams)

@schedule_bp.route('/api/shifts/<int:site_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_shifts(site_id):
    if current_user.role not in ['Admin', 'Supervisor']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    from models import Shift
    
    if request.method == 'GET':
        shifts = Shift.query.filter_by(site_id=site_id).all()
        return jsonify([{
            'id': s.id,
            'name': s.name,
            'start_time': s.start_time.strftime('%H:%M'),
            'end_time': s.end_time.strftime('%H:%M')
        } for s in shifts])
        
    elif request.method == 'POST':
        data = request.json
        shift = Shift(
            site_id=site_id,
            name=data.get('name'),
            start_time=datetime.strptime(data.get('start_time'), '%H:%M').time(),
            end_time=datetime.strptime(data.get('end_time'), '%H:%M').time()
        )
        db.session.add(shift)
        try:
            db.session.commit()
            return jsonify({'success': True, 'id': shift.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    elif request.method == 'DELETE':
        shift_id = request.args.get('id')
        shift = Shift.query.get_or_404(shift_id)
        db.session.delete(shift)
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/shift_assignments/<int:site_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_shift_assignments(site_id):
    if current_user.role not in ['Admin', 'Supervisor']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    from models import Shift, UserShift
    
    if request.method == 'GET':
        # Get all shifts for this site to filter user_shifts
        shifts = Shift.query.filter_by(site_id=site_id).all()
        shift_ids = [s.id for s in shifts]
        
        assignments = UserShift.query.filter(UserShift.shift_id.in_(shift_ids)).all()
        
        events = []
        for a in assignments:
            shift_name = a.shift.name.lower()
            if 'siang' in shift_name:
                color = '#22c55e' # Green
                order = 1
            elif 'pagi' in shift_name:
                color = '#0ea5e9' # Blue
                order = 2
            elif 'reguler' in shift_name:
                color = '#6b7280' # Gray
                order = 3
            elif 'cuti' in shift_name:
                color = '#eab308' # Yellow
                order = 4
            elif 'libur' in shift_name:
                color = '#ef4444' # Red
                order = 5
            else:
                color = '#94a3b8' # Default slate
                order = 6
                
            events.append({
                'id': a.id,
                'title': f"{a.user.name} - {a.shift.name}",
                'start': a.date.isoformat(),
                'backgroundColor': color,
                'borderColor': color,
                'allDay': True,
                'order': order,
                'extendedProps': {
                    'user_id': a.user_id,
                    'shift_id': a.shift_id,
                    'shift_name': a.shift.name
                }
            })
        return jsonify(events)
        
    elif request.method == 'POST':
        data = request.json
        shift_id = data.get('shift_id')
        date_str = data.get('date')
        user_ids = data.get('user_ids', [])
        team_id = data.get('team_id')
        
        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            from models import User
            
            if team_id:
                team_users = User.query.filter_by(team_id=team_id).all()
                user_ids.extend([u.id for u in team_users])
                
            # Remove duplicates
            user_ids = list(set(user_ids))
            
            if not user_ids:
                return jsonify({'success': False, 'error': 'No users selected'}), 400
                
            new_assignments = []
            for uid in user_ids:
                assignment = UserShift(
                    user_id=uid,
                    shift_id=shift_id,
                    date=date_val
                )
                db.session.add(assignment)
                new_assignments.append(assignment)
                
            db.session.commit()
            return jsonify({'success': True, 'ids': [a.id for a in new_assignments]})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
            
    elif request.method == 'DELETE':
        assignment_id = request.args.get('id')
        assignment = UserShift.query.get_or_404(assignment_id)
        db.session.delete(assignment)
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/events')
@login_required
def api_events():
    if current_user.role not in ['Admin', 'Supervisor']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    tech_id = request.args.get('technician_id')
    
    from models import Asset
    query = WorkOrder.query
    
    # Site filtering: non-admin only sees WOs from their site
    if current_user.role != 'Admin' and current_user.site_id:
        query = query.join(Asset).filter(Asset.site_id == current_user.site_id)
    
    if tech_id:
        query = query.filter(WorkOrder.assignees.any(id=int(tech_id)))
        
    work_orders = query.all()
    
    events = []
    
    # Generate some simple determinist colors for technicians
    tech_colors = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6']
    
    for wo in work_orders:
        if not wo.suggested_start_date:
            continue # Skip WOs clearly not scheduled yet
            
        start_date = wo.suggested_start_date.isoformat()
        end_date = wo.suggested_completion_date.isoformat() if wo.suggested_completion_date else start_date
        
        # Color specific to the primary assignee for visual grouping
        primary_color = '#64748b' # default slate
        titles = []
        if wo.assignees:
            primary_id = wo.assignees[0].id
            primary_color = tech_colors[primary_id % len(tech_colors)]
            titles.append(f"[{wo.assignees[0].name}]")
            
        site_name = wo.asset.site.name if (wo.asset and getattr(wo.asset, 'site', None)) else 'Unknown Site'
        titles.append(f"{wo.code} - {site_name}")
        
        title = " ".join(titles)
        
        events.append({
            'id': wo.id,
            'title': title,
            'start': start_date,
            'end': end_date,
            'backgroundColor': primary_color,
            'borderColor': primary_color,
            'url': url_for('work_orders.edit', id=wo.id), # Clicking goes to WO details
            'extendedProps': {
                'wo_code': wo.code,
                'status': wo.current_status.name if wo.current_status else 'Draft',
                'description': wo.description if hasattr(wo, 'description') else '',
                'asset': wo.asset.name if wo.asset else 'No Asset'
            }
        })
        
    return jsonify(events)

@schedule_bp.route('/api/update_event', methods=['POST'])
@login_required
def api_update_event():
    if current_user.role not in ['Admin', 'Supervisor']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    wo_id = data.get('id')
    new_start_str = data.get('start')
    new_end_str = data.get('end')
    
    wo = WorkOrder.query.get_or_404(wo_id)
    
    if new_start_str:
        try:
            # FullCalendar sends ISO strings like 2026-04-03T10:00:00Z
            start_dt = datetime.fromisoformat(new_start_str.replace('Z', '+00:00')).replace(tzinfo=None)
            wo.suggested_start_date = start_dt
        except Exception as e:
            pass
            
    if new_end_str:
        try:
            end_dt = datetime.fromisoformat(new_end_str.replace('Z', '+00:00')).replace(tzinfo=None)
            wo.suggested_completion_date = end_dt
        except Exception:
            pass
            
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/quick_assign', methods=['POST'])
@login_required
def api_quick_assign():
    if current_user.role not in ['Admin', 'Supervisor']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    from models import Asset, WorkOrderStatus
    data = request.json
    
    try:
        # Create a simplified Work Order to act as a Schedule Assignment
        code = f"SCH-{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d%H%M%S')}"
        status = WorkOrderStatus.query.filter_by(control_type='Active').first() or WorkOrderStatus.query.first()
        
        new_wo = WorkOrder(
            code=code,
            description=data.get('description', 'Scheduled Task'),
            asset_id=data.get('asset_id'),
            maintenance_type='Other', # General schedule
            status_id=status.id if status else None,
            priority='Medium'
        )
        
        start_dt = data.get('start_date')
        end_dt = data.get('end_date')
        if start_dt:
            new_wo.suggested_start_date = datetime.strptime(start_dt, '%Y-%m-%dT%H:%M')
        if end_dt:
            new_wo.suggested_completion_date = datetime.strptime(end_dt, '%Y-%m-%dT%H:%M')
            
        db.session.add(new_wo)
        db.session.flush() # to get id
        
        # Add assignees
        tech_id = data.get('technician_id')
        if tech_id:
            tech = db.session.get(User, tech_id)
            if tech:
                new_wo.assignees.append(tech)
                
        # Log Creation
        l = WorkOrderLog(work_order_id=new_wo.id, user_id=current_user.id, log_text="Work Order created (Scheduled).")
        db.session.add(l)
                
        db.session.commit()
        return jsonify({'success': True, 'wo_id': new_wo.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@schedule_bp.route('/api/kanban_events')
@login_required
def api_kanban_events():
    if current_user.role not in ['Admin', 'Supervisor']:
        return jsonify({'error': 'Unauthorized'}), 403
        
    tech_id = request.args.get('technician_id')
    
    from models import Asset, WorkOrderStatus
    query = WorkOrder.query
    
    if current_user.role != 'Admin' and current_user.site_id:
        query = query.join(Asset).filter(Asset.site_id == current_user.site_id)
        
    if tech_id:
        query = query.filter(WorkOrder.assignees.any(id=int(tech_id)))
        
    # Only fetch non-closed to avoid huge payloads, or at least order by id desc
    # For now, let's fetch everything that is not 'Closed' control type if possible, or limit to 200
    work_orders = query.join(WorkOrderStatus, WorkOrder.status_id == WorkOrderStatus.id, isouter=True) \
                       .filter(db.or_(WorkOrderStatus.control_type != 'Closed', WorkOrderStatus.id == None)) \
                       .order_by(WorkOrder.id.desc()).limit(200).all()
    
    events = []
    for wo in work_orders:
        site_name = wo.asset.site.name if (wo.asset and getattr(wo.asset, 'site', None)) else 'Unknown Site'
        
        events.append({
            'id': wo.id,
            'code': wo.code,
            'description': wo.description,
            'status_id': wo.status_id,
            'priority': wo.priority,
            'site': site_name,
            'assignees': [a.name for a in wo.assignees]
        })
        
    return jsonify(events)

@schedule_bp.route('/api/update_wo_status', methods=['POST'])
@login_required
def api_update_wo_status():
    if current_user.role not in ['Admin', 'Supervisor']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    wo_id = data.get('wo_id')
    new_status_id = data.get('status_id')
    
    wo = WorkOrder.query.get_or_404(wo_id)
    if new_status_id:
        wo.status_id = new_status_id
        try:
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Invalid status'}), 400
