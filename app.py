import os
import locale
from dotenv import load_dotenv

load_dotenv()

try:
    locale.setlocale(locale.LC_TIME, 'Indonesian_Indonesia.1252')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'id_ID.utf8')
    except:
        pass

from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from flask_login import LoginManager, current_user, login_required
from flask_babel import Babel, _
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, User

def get_locale():
    return session.get('lang', 'id')

babel = Babel(locale_selector=get_locale)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["50000 per day", "5000 per hour"],
    storage_uri="memory://"
)

def create_app():
    from datetime import timedelta
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    
    # Session and CSRF lifetime (30 minutes for ISO 27001)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['WTF_CSRF_TIME_LIMIT'] = 604800
    
    # Performance Optimization: Cache & Compression
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000 # 1 year cache for static files
    
    try:
        from flask_compress import Compress
        Compress(app)
    except ImportError:
        pass
        
    # Database Configuration
    basedir = os.path.abspath(os.path.dirname(__name__))
    db_url = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Engine configuration for MySQL to prevent connection drops
    if db_url.startswith('mysql'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'pool_size': 10,
            'max_overflow': 20,
        }

    # Initialize extensions
    db.init_app(app)
    babel.init_app(app)
    limiter.init_app(app)
    
    # Security: ProxyFix for Cloudflare/Reverse Proxies
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Security: CSRF Protection
    try:
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect(app)
    except ImportError:
        print("Warning: Flask-WTF not installed. Using dummy csrf_token to prevent template errors.")
        @app.context_processor
        def inject_dummy_csrf():
            return dict(csrf_token=lambda: "")
            
    # Custom Jinja filters
    @app.template_filter('to_jakarta')
    def to_jakarta(dt, fmt=None):
        if not dt:
            return ""
        from datetime import timedelta
        local_dt = dt + timedelta(hours=7)
        if fmt:
            return local_dt.strftime(fmt)
        return local_dt.strftime('%Y-%m-%d %H:%M:%S')
        
    # Security: HTTP Headers (CSP, HSTS) & Cookies
    try:
        from flask_talisman import Talisman
        csp = {
            'default-src': [
                '\'self\'',
                'https://cdn.jsdelivr.net',
                'https://fonts.googleapis.com',
                'https://fonts.gstatic.com',
                'https://unpkg.com',
                'https://n8n-2.weebsite.my.id',
                'https://cdnjs.cloudflare.com',
                'data:'
            ],
            'img-src': ['\'self\'', 'data:', 'https:'],
            'script-src': [
                '\'self\'',
                '\'unsafe-inline\'',
                '\'unsafe-eval\'',
                'https://cdn.jsdelivr.net',
                'https://unpkg.com',
                'https://code.jquery.com',
                'https://static.cloudflareinsights.com',
                'https://cdnjs.cloudflare.com'
            ],
            'style-src': [
                '\'self\'',
                '\'unsafe-inline\'',
                'https://cdn.jsdelivr.net',
                'https://fonts.googleapis.com',
                'https://cdnjs.cloudflare.com'
            ],
            'frame-src': ['*'],
            'connect-src': ['*']
        }
        is_production = os.environ.get('APP_ENV') == 'production'
        Talisman(app, content_security_policy=csp, force_https=is_production, session_cookie_secure=is_production, session_cookie_http_only=True, session_cookie_samesite='Lax')
    except ImportError:
        print("Warning: Flask-Talisman not installed")

    # SQLite WAL mode — allow concurrent reads during writes, prevent "database is locked"
    import sqlite3
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")  # Wait 5s if locked, don't crash
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
            cursor.close()
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Import and register blueprints
    from auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from assets import assets_bp
    app.register_blueprint(assets_bp)
    
    from work_orders import work_orders_bp
    app.register_blueprint(work_orders_bp)
    
    from settings import settings_bp
    app.register_blueprint(settings_bp)
    
    from warehouse import warehouse_bp
    app.register_blueprint(warehouse_bp)
    
    from purchasing import purchasing_bp
    app.register_blueprint(purchasing_bp)
    
    from reports import reports_bp
    app.register_blueprint(reports_bp)

    from helpdesk import helpdesk_bp
    app.register_blueprint(helpdesk_bp)

    from schedule import schedule_bp
    app.register_blueprint(schedule_bp)

    from chiller_monitoring import chiller_monitoring_bp
    app.register_blueprint(chiller_monitoring_bp)
    
    from bas_monitoring import bas_monitoring_bp
    app.register_blueprint(bas_monitoring_bp)
    
    from custom_dashboards import custom_dashboards_bp
    app.register_blueprint(custom_dashboards_bp)

    from verify import verify_bp
    app.register_blueprint(verify_bp)

    @app.route('/download-app')
    def download_app():
        return render_template('download_app.html')

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/set_lang/<lang>')
    def set_lang(lang):
        if lang in ['id', 'en']:
            session['lang'] = lang
        return redirect(request.referrer or url_for('dashboard'))

    from models import WorkOrder, Asset, Part, StockLevel, PurchaseOrder, WorkOrderStatus, HelpdeskTicket, Site, UserDashboardWidget, CustomSidebarLink
    from dashboard_widgets import get_catalog_for_role, get_default_layout, WIDGET_CATALOG, get_widget_info
    
    @app.route('/chatbot')
    @login_required
    def chatbot_page():
        if current_user.role != 'Admin':
            flash('Akses hanya untuk Admin.', 'danger')
            return redirect(url_for('dashboard'))
        return render_template('chatbot.html')
    
    @app.route('/user_activity')
    @login_required
    def user_activity():
        if current_user.role != 'Admin':
            flash('Akses hanya untuk Admin.', 'danger')
            return redirect(url_for('dashboard'))
            
        if current_user.site_id:
            users = User.query.filter_by(site_id=current_user.site_id).order_by(User.login_count.desc()).all()
        else:
            users = User.query.order_by(User.login_count.desc()).all()
        
        # Summary metrics
        total_logins = sum(u.login_count or 0 for u in users)
        most_active_user = users[0] if users else None
        
        return render_template('user_activity.html', 
                               users=users, 
                               total_logins=total_logins,
                               most_active_user=most_active_user)
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.role == 'User':
            return redirect(url_for('helpdesk.index'))
            
        from sqlalchemy import func
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        selected_site_id = request.args.get('site_id', type=int)
        
        # --- Time Range Filtering ---
        time_range = request.args.get('time_range', 'this_month')
        import calendar
        start_date = None
        end_date = None
        
        if time_range == 'this_month':
            start_date = datetime(now.year, now.month, 1)
            _, last_day = calendar.monthrange(now.year, now.month)
            end_date = datetime(now.year, now.month, last_day, 23, 59, 59)
        elif time_range == 'last_month':
            last_month = now.month - 1 if now.month > 1 else 12
            year = now.year if now.month > 1 else now.year - 1
            start_date = datetime(year, last_month, 1)
            _, last_day = calendar.monthrange(year, last_month)
            end_date = datetime(year, last_month, last_day, 23, 59, 59)
        elif time_range == 'this_year':
            start_date = datetime(now.year, 1, 1)
            end_date = datetime(now.year, 12, 31, 23, 59, 59)
        elif time_range == 'custom':
            start_str = request.args.get('start_date')
            end_str = request.args.get('end_date')
            if start_str and end_str:
                try:
                    start_date = datetime.strptime(start_str, '%Y-%m-%d')
                    end_date = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                except ValueError:
                    pass
        
        filter_site_id = current_user.site_id
        if not filter_site_id and selected_site_id:
            filter_site_id = selected_site_id
            
        available_sites = []
        if not current_user.site_id:
            available_sites = Site.query.all()
        
        # --- Load user's widget layout ---
        saved_widgets = UserDashboardWidget.query.filter_by(user_id=current_user.id).order_by(UserDashboardWidget.position).all()
        if saved_widgets:
            user_widgets = [
                {'widget_key': w.widget_key, 'position': w.position, 'col_span': w.col_span, 'is_visible': w.is_visible}
                for w in saved_widgets if w.is_visible
            ]
        else:
            user_widgets = get_default_layout(current_user.role)
        
        # Build catalog for "Add Widget" panel
        widget_catalog = get_catalog_for_role(current_user.role)
        active_keys = [w['widget_key'] for w in user_widgets]
        
        # 1. Status Work Order Chart
        from sqlalchemy.orm import selectinload
        from sqlalchemy import func
        query = WorkOrder.query.options(selectinload(WorkOrder.current_status))
        if filter_site_id:
            query = query.join(Asset).filter(Asset.site_id == filter_site_id)
            
        if start_date and end_date:
            query = query.filter(
                func.coalesce(WorkOrder.suggested_completion_date, WorkOrder.date_created) >= start_date, 
                func.coalesce(WorkOrder.suggested_completion_date, WorkOrder.date_created) <= end_date
            )
            
        if current_user.role == 'Technician':
            query = query.filter(WorkOrder.assignees.any(id=current_user.id))
            
        all_wos_raw = query.all()
        
        all_wos = []
        draft_wos_count = 0
        
        for wo in all_wos_raw:
            if wo.current_status and wo.current_status.name == 'Draft':
                draft_wos_count += 1
            else:
                all_wos.append(wo)

        status_counts = {}
        for wo in all_wos:
            if not wo.current_status:
                continue
            name = wo.current_status.name
            status_counts[name] = status_counts.get(name, 0) + 1
            
        # Optional: Define logical ordering and colors for statuses to match Kanban
        color_map = {
            'Completed': '#10b981',   # emerald
            'Assigned': '#0ea5e9',    # sky
            'In Progress': '#3b82f6', # blue
            'Hold': '#f59e0b',        # amber
            'Solved': '#8b5cf6',      # violet
            'Incompleted': '#ef4444'  # red
        }
        
        ordered_statuses = ['Completed', 'Assigned', 'In Progress', 'Hold', 'Solved', 'Incompleted']
        wo_status_labels = []
        wo_status_data = []
        wo_status_colors = []
        
        # Add statuses in order (even if 0)
        for st in ordered_statuses:
            wo_status_labels.append(st)
            wo_status_data.append(status_counts.get(st, 0))
            wo_status_colors.append(color_map.get(st, '#94a3b8'))
            if st in status_counts:
                del status_counts[st]
                
        # Add any remaining unknown statuses
        for st, count in status_counts.items():
            wo_status_labels.append(st)
            wo_status_data.append(count)
            wo_status_colors.append('#94a3b8') # default slate-400

        
        # 2. Maintenance KPIs (MTBF, MTTR, PM Compliance)
        total_repair_hours = 0
        completed_wos = [w for w in all_wos if w.current_status and w.current_status.control_type == 'Closed']
        
        for wo in completed_wos:
            if wo.start_date and wo.end_date and wo.end_date > wo.start_date:
                total_repair_hours += (wo.end_date - wo.start_date).total_seconds() / 3600
                
        mttr_hours = round(total_repair_hours / len(completed_wos), 1) if completed_wos else 0
        mttr_tooltip = f"{round(total_repair_hours, 1)} Jam Perbaikan / {len(completed_wos)} WO Selesai"
        
        if filter_site_id:
            online_assets_count = Asset.query.filter_by(status='Online', site_id=filter_site_id).count()
            total_assets = Asset.query.filter_by(site_id=filter_site_id).count()
        else:
            online_assets_count = Asset.query.filter_by(status='Online').count()
            total_assets = Asset.query.count()
        asset_availability = round((online_assets_count / total_assets) * 100, 1) if total_assets > 0 else 0
        
        corrective_wos = [w for w in all_wos if w.maintenance_type == 'Corrective']
        
        # Calculate dynamic hours based on the selected time range
        if start_date and end_date:
            delta = end_date - start_date
            period_hours = delta.total_seconds() / 3600
        else:
            period_hours = 30 * 24 # Fallback to 30 days
            
        # Total Jam Kerja Semua Aset
        total_uptime_hours = total_assets * period_hours
        
        # MTBF = Total Jam Kerja Semua Aset / Total Semua Insiden Kerusakan
        # Jika tidak ada kerusakan (0), maka MTBF sama dengan total jam kerja (waktu tanpa putus)
        mtbf_hours = round(total_uptime_hours / len(corrective_wos), 1) if len(corrective_wos) > 0 else round(total_uptime_hours, 1)
        mtbf_tooltip = f"{total_assets} Aset × {round(period_hours, 1)} Jam / {len(corrective_wos)} WO Corrective"
        
        pm_wos = [w for w in all_wos if w.maintenance_type == 'Preventive' and w.suggested_completion_date]
        compliant_pm = 0
        for wo in pm_wos:
            if wo.current_status and wo.current_status.control_type == 'Closed':
                if wo.end_date and wo.end_date <= wo.suggested_completion_date:
                    compliant_pm += 1
            else:
                if now <= wo.suggested_completion_date:
                    compliant_pm += 1
        pm_compliance = round((compliant_pm / len(pm_wos)) * 100, 1) if pm_wos else 100
        
        # 3. Downtime & Kondisi Aset (Top 5 Downtime)
        asset_downtime = {}
        for wo in completed_wos:
            if wo.asset_id and wo.start_date and wo.end_date and wo.end_date > wo.start_date:
                hrs = (wo.end_date - wo.start_date).total_seconds() / 3600
                asset_downtime[wo.asset_id] = asset_downtime.get(wo.asset_id, 0) + hrs
                
        top_down_ids = sorted(asset_downtime, key=asset_downtime.get, reverse=True)[:5]
        top_downtime_assets = []
        for aid in top_down_ids:
            ast = db.session.get(Asset, aid)
            if ast:
                top_downtime_assets.append({
                    'id': ast.id,
                    'name': ast.name, 
                    'code': ast.code, 
                    'hours': round(asset_downtime[aid], 1)
                })
        
        # --- CPI CALCULATION ---
        from models import AssetMeter, AssetMeterReading
        if filter_site_id:
            cpi_assets = Asset.query.filter_by(site_id=filter_site_id, is_chiller=True).all()
        else:
            cpi_assets = Asset.query.filter_by(is_chiller=True).all()
            
        cpi_data = []
        thirty_days_ago = now - timedelta(days=30)
        
        for asset in cpi_assets:
            required_meters = ['Design kW/TR', 'Actual kW/TR', 'Actual Cond Approach Temp (°C)']
            asset_meters = {m.name: m for m in asset.meters.all()}
            for rm in required_meters:
                if rm not in asset_meters:
                    new_m = AssetMeter(asset_id=asset.id, name=rm, unit='kW/TR' if 'kW' in rm else '°C')
                    db.session.add(new_m)
                    asset_meters[rm] = new_m
                    
            db.session.flush()
            
            def get_latest_reading(meter_name):
                m = asset_meters.get(meter_name)
                if not m: return None
                latest = AssetMeterReading.query.filter_by(meter_id=m.id).order_by(AssetMeterReading.reading_date.desc()).first()
                return latest.reading_value if latest else None
                
            design_eff = get_latest_reading('Design kW/TR')
            actual_eff = get_latest_reading('Actual kW/TR')
            approach_temp = get_latest_reading('Actual Cond Approach Temp (°C)')
            
            asset_wos = WorkOrder.query.filter_by(asset_id=asset.id, maintenance_type='Corrective').filter(WorkOrder.date_created >= thirty_days_ago).count()
            score_reliability = max(0.0, 40.0 - (asset_wos * 10.0))
            
            score_efficiency = 30.0
            if design_eff and actual_eff and design_eff > 0:
                deviation = (actual_eff - design_eff) / design_eff
                if deviation > 0:
                    score_efficiency = max(0.0, 30.0 - (deviation * 100))
                    
            score_fouling = 20.0
            if approach_temp is not None:
                if approach_temp > 2.0:
                    score_fouling = max(0.0, 20.0 - ((approach_temp - 2.0) * 10.0))
                    
            score_ops = 10.0 if asset.status == 'Online' else 0.0
            final_cpi = round(score_reliability + score_efficiency + score_fouling + score_ops, 1)
            
            if final_cpi >= 85: color = 'success'
            elif final_cpi >= 70: color = 'warning'
            else: color = 'danger'
            
            cpi_data.append({
                'asset': asset,
                'score': final_cpi,
                'color': color,
                'eff': actual_eff if actual_eff else '-',
                'wos_30d': asset_wos,
                'breakdown': {
                    'reliability': round(score_reliability, 1),
                    'efficiency': round(score_efficiency, 1),
                    'fouling': round(score_fouling, 1),
                    'ops': round(score_ops, 1)
                }
            })
            
        db.session.commit()
        cpi_data.sort(key=lambda x: x['score'])
        top_lowest_cpi = cpi_data[:5]
        
        # 4. Inventory
        if filter_site_id:
            low_stock_items = StockLevel.query.filter(StockLevel.qty_on_hand <= StockLevel.min_qty, StockLevel.site_id == filter_site_id).limit(10).all()
            pending_prs = PurchaseOrder.query.filter(PurchaseOrder.status.in_(['Draft', 'Submitted', 'Pending']), PurchaseOrder.site_id == filter_site_id).limit(10).all()
        else:
            low_stock_items = StockLevel.query.filter(StockLevel.qty_on_hand <= StockLevel.min_qty).limit(10).all()
            pending_prs = PurchaseOrder.query.filter(PurchaseOrder.status.in_(['Draft', 'Submitted', 'Pending'])).limit(10).all()
        
        # 4.5 Overdue and Upcoming WOs
        # Overdue WOs: User requested that WOs are only overdue if they have passed the filter's start date 
        # (e.g. passing the month). We don't use all_wos because all_wos is filtered by date_created >= start_date.
        overdue_query = WorkOrder.query.join(WorkOrderStatus, WorkOrder.status_id == WorkOrderStatus.id).filter(
            WorkOrderStatus.control_type != 'Closed'
        )
        if filter_site_id:
            overdue_query = overdue_query.join(Asset).filter(Asset.site_id == filter_site_id)
            
        if current_user.role == 'Technician':
            overdue_query = overdue_query.filter(WorkOrder.assignees.any(id=current_user.id))
            
        if start_date:
            # Overdue means the target date has passed the start of our filter period
            overdue_wos_list = overdue_query.filter(WorkOrder.suggested_completion_date < start_date).all()
        else:
            # If no start_date, fallback to now
            overdue_wos_list = overdue_query.filter(WorkOrder.suggested_completion_date < now).all()

        upcoming_wos_list = []
        for wo in all_wos:
            if wo.current_status and wo.current_status.control_type == 'Closed':
                continue
            if wo.suggested_completion_date:
                # If a WO is in all_wos, its date_created is >= start_date.
                # So if its target date is >= start_date, it's upcoming for this period.
                # We also need to check if it's strictly > end_date to exclude it.
                if end_date and wo.suggested_completion_date > end_date:
                    continue
                
                # Check if it's already considered overdue by the new logic
                if start_date and wo.suggested_completion_date < start_date:
                    continue
                elif not start_date and wo.suggested_completion_date < now:
                    continue
                    
                upcoming_wos_list.append(wo)
                    
        overdue_wos_list.sort(key=lambda x: x.suggested_completion_date)
        upcoming_wos_list.sort(key=lambda x: x.suggested_completion_date)
        
        overdue_wos_count = len(overdue_wos_list)
        upcoming_wos_count = len(upcoming_wos_list)
        
        overdue_wos = overdue_wos_list[:5]
        upcoming_wos = upcoming_wos_list[:5]
        
        # 5. Calendar
        calendar_events = []
        for wo in all_wos:
            event_date = wo.suggested_completion_date or wo.date_created
            if event_date:
                # Add prefix for different types
                if wo.maintenance_type == 'Preventive':
                    prefix = 'PM'
                elif wo.maintenance_type == 'Corrective':
                    prefix = 'CM'
                elif wo.maintenance_type == 'Breakdown':
                    prefix = 'BD'
                else:
                    prefix = 'WO'
                    
                asset_name = wo.asset.name if wo.asset else 'No Asset'
                title = f"{prefix}: {asset_name}"
                
                color = '#4e73df' # Default blue
                if wo.current_status:
                    status_name = wo.current_status.name
                    color_map_cal = {
                        'Completed': '#10b981',   # emerald
                        'Draft': '#64748b',       # slate
                        'Assigned': '#0ea5e9',    # sky
                        'In Progress': '#3b82f6', # blue
                        'Hold': '#f59e0b',        # amber
                        'Solved': '#8b5cf6',      # violet
                        'Incompleted': '#be123c'  # rose
                    }
                    color = color_map_cal.get(status_name, '#4e73df')
                    
                    # Override to red if overdue and not in a finalized state
                    if status_name not in ['Completed', 'Closed', 'Solved', 'Incompleted'] and now > event_date:
                        color = '#e74a3b' # Red for truly overdue
                
                calendar_events.append({
                    'id': wo.id,
                    'title': title,
                    'start': event_date.strftime('%Y-%m-%d'),
                    'url': url_for('work_orders.edit', id=wo.id),
                    'color': color
                })
        
        # 6. Expiring Assets (End of Life / Warranty)
        if filter_site_id:
            all_assets_for_exp = Asset.query.filter_by(site_id=filter_site_id).all()
        else:
            all_assets_for_exp = Asset.query.all()
            
        expiring_assets = []
        for ast in all_assets_for_exp:            
            if ast.end_date and ast.end_date >= now:
                days_left = (ast.end_date - now).days
                if days_left <= 365:
                    expiring_assets.append({
                        'asset': ast,
                        'expiry_date': ast.end_date,
                        'days_left': days_left,
                        'exp_type': "End of Life"
                    })
                
            for w in ast.warranties.all():
                if w.expiry_date and w.expiry_date >= now:
                    days_left = (w.expiry_date - now).days
                    if days_left <= 365:
                        exp_type = f"Warranty"
                        if w.type:
                            exp_type += f" ({w.type})"
                        expiring_assets.append({
                            'asset': ast,
                            'expiry_date': w.expiry_date,
                            'days_left': days_left,
                            'exp_type': exp_type
                        })
            
            for cf in ast.custom_fields.all():
                if cf.expiry_date and cf.expiry_date >= now:
                    days_left = (cf.expiry_date - now).days
                    if days_left <= 365:
                        expiring_assets.append({
                            'asset': ast,
                            'expiry_date': cf.expiry_date,
                            'days_left': days_left,
                            'exp_type': f"Komponen ({cf.field_name})"
                        })
                    
        expiring_assets.sort(key=lambda x: x['days_left'])
        
        start_date_str = start_date.strftime('%Y-%m-%d') if start_date else ''
        end_date_str = end_date.strftime('%Y-%m-%d') if end_date else ''

        # Calculate extra metrics for executive view
        active_breakdowns = sum(1 for wo in all_wos if wo.current_status and wo.current_status.control_type != 'Closed' and getattr(wo, 'priority', '') == 'Critical')
        
        active_alerts = []
        for wo in overdue_wos: # taking from overdue_wos which is already sorted
            days_open = (now - wo.date_created).days if wo.date_created else 0
            active_alerts.append({
                'code': wo.code,
                'asset_name': wo.asset.name if wo.asset else 'No Asset',
                'issue': wo.description[:30] if wo.description else '',
                'days_open': days_open
            })
            if len(active_alerts) >= 3:
                break
                
        view_mode = request.args.get('view', '')
        template = 'dashboard/executive.html' if view_mode == 'executive' else 'dashboard.html'

        return render_template(template, 
                               draft_wos_count=draft_wos_count,
                               wo_status_labels=wo_status_labels,
                               wo_status_data=wo_status_data,
                               wo_status_colors=wo_status_colors,
                               mttr_hours=mttr_hours,
                               mttr_tooltip=mttr_tooltip,
                               mtbf_hours=mtbf_hours,
                               mtbf_tooltip=mtbf_tooltip,
                               pm_compliance=pm_compliance,
                               asset_availability=asset_availability,
                               top_downtime_assets=top_downtime_assets,
                               top_lowest_cpi=top_lowest_cpi,
                               low_stock_items=low_stock_items,
                               pending_prs=pending_prs,
                               overdue_wos=overdue_wos,
                               upcoming_wos=upcoming_wos,
                               overdue_wos_count=overdue_wos_count,
                               upcoming_wos_count=upcoming_wos_count,
                               total_wos_count=len(all_wos),
                               completed_wos_count=len(completed_wos),
                               expiring_assets=expiring_assets,
                               calendar_events=calendar_events,
                               available_sites=available_sites,
                               selected_site_id=selected_site_id,
                               user_widgets=user_widgets,
                               widget_catalog=widget_catalog,
                               active_keys=active_keys,
                               time_range=time_range,
                               start_date_str=start_date_str,
                               end_date_str=end_date_str,
                               active_breakdowns=active_breakdowns,
                               active_alerts=active_alerts,
                               total_assets=total_assets)

    # ============================================
    # LOGSHEET SCHEDULE ROUTES - For Admin/Supervisor
    # ============================================
    @app.route('/dashboard/logsheet_management')
    @login_required
    def logsheet_management():
        """Unified Logsheet Management (Schedules and Records)"""
        from sqlalchemy.orm import selectinload
        from models import Logsheet, LogsheetSchedule, Site, User
        from datetime import date, datetime
        
        tab = request.args.get('tab', 'schedules')
        today = date.today()
        
        if current_user.site_id:
            assets = Asset.query.filter_by(site_id=current_user.site_id).all()
            sites = Site.query.filter_by(id=current_user.site_id).all()
            users = User.query.filter(User.role.in_(['Technician', 'Supervisor', 'Admin']), User.site_id == current_user.site_id).all()
        else:
            assets = Asset.query.all()
            sites = Site.query.all()
            users = User.query.filter(User.role.in_(['Technician', 'Supervisor', 'Admin'])).all()
        
        schedules = []
        logsheets = []
        
        view = request.args.get('view', 'pending') # legacy for schedule
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        status_filter = request.args.get('status')
        asset_id = request.args.get('asset_id')
        site_id = request.args.get('site_id')
        user_id = request.args.get('user_id')
        q = request.args.get('q', '')
        
        # Fetch schedules that haven't been started (Scheduled)
        sched_query = LogsheetSchedule.query.options(
            selectinload(LogsheetSchedule.asset),
            selectinload(LogsheetSchedule.site),
            selectinload(LogsheetSchedule.assigned_technicians),
            selectinload(LogsheetSchedule.created_by)
        ).filter(LogsheetSchedule.status == 'Scheduled')
        
        # Fetch logsheets (Draft, Submitted, Approved)
        log_query = Logsheet.query.options(
            selectinload(Logsheet.asset),
            selectinload(Logsheet.site),
            selectinload(Logsheet.filled_by),
            selectinload(Logsheet.logsheet_schedule)
        )
        
        # Apply Filters
        if current_user.site_id:
            sched_query = sched_query.filter(LogsheetSchedule.site_id == current_user.site_id)
            log_query = log_query.filter(Logsheet.site_id == current_user.site_id)
            
        if site_id:
            sched_query = sched_query.filter(LogsheetSchedule.site_id == int(site_id))
            log_query = log_query.filter(Logsheet.site_id == int(site_id))
            
        if user_id:
            sched_query = sched_query.filter(LogsheetSchedule.assigned_technicians.any(id=int(user_id)))
            log_query = log_query.filter(Logsheet.filled_by_id == int(user_id))
            
        if status_filter:
            if status_filter == 'Scheduled':
                log_query = log_query.filter(Logsheet.id == -1) # None
            else:
                sched_query = sched_query.filter(LogsheetSchedule.id == -1) # None
                log_query = log_query.filter(Logsheet.status == status_filter)
                
        if q:
            sched_query = sched_query.filter((LogsheetSchedule.code.ilike(f'%{q}%')) | (LogsheetSchedule.name.ilike(f'%{q}%')))
            log_query = log_query.filter((Logsheet.code.ilike(f'%{q}%')))
            
        schedules = sched_query.all()
        logsheets = log_query.all()
        
        # Helper to determine shift
        def get_shift_by_time(t):
            if not t:
                return 'Unassigned'
            # Assuming t is a time object or datetime object
            hour = getattr(t, 'hour', 0)
            if 4 <= hour < 12:
                return '1'
            elif 12 <= hour < 20:
                return '2'
            else:
                return '3'

        # Merge them into a single dictionary
        shift_groups = {
            '1': [],
            '2': [],
            '3': []
        }
        for s in schedules:
            shift = get_shift_by_time(s.scheduled_time)
            if shift not in shift_groups:
                shift_groups[shift] = []
            shift_groups[shift].append({
                'type': 'schedule',
                'obj': s,
                'date': s.scheduled_date
            })
        for l in logsheets:
            time_to_use = l.logsheet_schedule.scheduled_time if (l.logsheet_schedule and l.logsheet_schedule.scheduled_time) else l.created_at
            shift = get_shift_by_time(time_to_use)
            if shift not in shift_groups:
                shift_groups[shift] = []
            shift_groups[shift].append({
                'type': 'logsheet',
                'obj': l,
                'date': l.date
            })
            
        # Sort each group by date descending
        has_any_items = False
        for shift, items_list in shift_groups.items():
            if items_list:
                has_any_items = True
            items_list.sort(key=lambda x: x['date'] if x['date'] else date.today(), reverse=True)
            
        sorted_shifts = sorted(shift_groups.keys())
            
        from models import Team
        teams = Team.query.all()
        return render_template('dashboard/logsheet_management.html',
                               shift_groups=shift_groups,
                               sorted_shifts=sorted_shifts,
                               has_any_items=has_any_items,
                               today=today,
                               assets=assets,
                               sites=sites,
                               users=users,
                               teams=teams,
                               date_from=date_from,
                               date_to=date_to,
                               status_filter=status_filter,
                               asset_id=asset_id,
                               site_id=site_id,
                               user_id=user_id,
                               q=q)

    @app.route('/dashboard/logsheet/schedule/add_adhoc', methods=['POST'])
    @login_required
    def logsheet_schedule_add_adhoc():
        from models import LogsheetSchedule, Asset, User
        from datetime import datetime, date
        
        asset_id = request.form.get('asset_id')
        check_time_str = request.form.get('check_time', '00:00')
        shift_name = request.form.get('shift_name', '1')
        
        if not asset_id:
            flash('Aset belum dipilih', 'warning')
            return redirect(url_for('logsheet_management', tab='schedules'))
            
        asset = Asset.query.get(asset_id)
        if not asset:
            flash('Aset tidak ditemukan', 'danger')
            return redirect(url_for('logsheet_management', tab='schedules'))
            
        today = date.today()
        date_str = today.strftime('%Y%m%d')
        latest_sched = LogsheetSchedule.query.filter(
            LogsheetSchedule.code.like(f'SCH-{date_str}-%')
        ).order_by(LogsheetSchedule.code.desc()).first()
        
        if latest_sched:
            try:
                count = int(latest_sched.code.split('-')[-1])
            except:
                count = 0
        else:
            count = 0
            
        code = f"SCH-{date_str}-{str(count + 1).zfill(3)}"
        
        from datetime import time
        h, m = check_time_str.split(':')
        check_time = time(int(h), int(m))
        
        team_id = request.form.get('team_id')
        
        # Automatically determine shift based on time
        hour = int(h)
        if 4 <= hour < 12:
            shift_val = '1'
        elif 12 <= hour < 20:
            shift_val = '2'
        else:
            shift_val = '3'

        schedule = LogsheetSchedule(
            code=code,
            name=asset.name,
            asset_id=asset.id,
            site_id=asset.site_id,
            scheduled_date=today,
            scheduled_time=check_time,
            shift=shift_val,
            status='Scheduled',
            created_by_id=current_user.id,
            team_id=team_id if team_id else None
        )
        db.session.add(schedule)
        db.session.flush()
        
        tech_ids = request.form.getlist('tech_id')
        
        if tech_ids:
            for t_id in tech_ids:
                tech = User.query.get(t_id)
                if tech:
                    schedule.assigned_technicians.append(tech)
                
        # Copy parameters from asset metering
        from models import AssetMeter, LogsheetScheduleParameter
        meters = AssetMeter.query.filter_by(asset_id=asset.id).all()
        for meter in meters:
            param = LogsheetScheduleParameter(
                schedule_id=schedule.id,
                name=meter.name,
                unit=meter.unit,
                entry_type='reading'
            )
            db.session.add(param)
            
        db.session.commit()
        flash(f'Tugas {asset.name} berhasil ditambahkan ke Shift {shift_val}', 'success')
        return redirect(url_for('logsheet_management', tab='schedules'))

    @app.route('/dashboard/logsheet/api/asset/<int:asset_id>/meters')
    @login_required
    def api_asset_meters(asset_id):
        from models import AssetMeter
        from flask import jsonify
        meters = AssetMeter.query.filter_by(asset_id=asset_id).all()
        return jsonify([{'name': m.name, 'unit': m.unit if m.unit != 'Checklist' else '', 'entry_type': 'reading', 'min': '', 'max': ''} for m in meters])

    @app.route('/dashboard/logsheet/schedule/create', methods=['GET', 'POST'])
    @login_required
    def logsheet_schedule_create():
        """Create a new logsheet schedule"""
        from models import LogsheetSchedule, LogsheetScheduleParameter, User
        from datetime import date, time

        if request.method == 'POST':
            name = request.form.get('name')
            asset_id = request.form.get('asset_id')
            scheduled_date = request.form.get('scheduled_date')
            scheduled_time = request.form.get('scheduled_time', '08:00')
            techs_raw = request.form.get('technicians', '')
            assigned_technicians = techs_raw.split(',') if techs_raw else []
            parameters_json = request.form.get('parameters_json', '[]')

            if not name or not asset_id or not scheduled_date:
                flash('Mohon lengkapi semua field wajib', 'warning')
                return redirect(url_for('logsheet_schedule_create'))

            # Generate code: SCH-YYYYMMDD-XXX
            date_str = scheduled_date.replace('-', '')
            latest_sched = LogsheetSchedule.query.filter(
                LogsheetSchedule.code.like(f'SCH-{date_str}-%')
            ).order_by(LogsheetSchedule.code.desc()).first()
            
            if latest_sched:
                try:
                    count = int(latest_sched.code.split('-')[-1])
                except:
                    count = 0
            else:
                count = 0
                
            code = f"SCH-{date_str}-{str(count + 1).zfill(3)}"

            # Get site from form or fallback to asset's site / user's site
            form_site_id = request.form.get('site_id')
            asset = Asset.query.get(asset_id)
            
            if form_site_id:
                site_id = int(form_site_id)
            else:
                site_id = asset.site_id if asset else (current_user.site_id or 1)

            # Parse time
            try:
                sched_time = time.fromisoformat(scheduled_time) if scheduled_time else None
            except:
                sched_time = time(8, 0)
                
            team_id = request.form.get('team_id')

            schedule = LogsheetSchedule(
                name=name,
                code=code,
                scheduled_date=date.fromisoformat(scheduled_date),
                scheduled_time=sched_time,
                asset_id=asset_id,
                site_id=site_id,
                created_by_id=current_user.id,
                team_id=team_id if team_id else None,
                status='Scheduled'
            )

            # Add technicians
            for tech_id in assigned_technicians:
                tech = User.query.get(int(tech_id))
                if tech:
                    schedule.assigned_technicians.append(tech)

            db.session.add(schedule)
            db.session.flush()

            # Add parameters
            import json
            try:
                params = json.loads(parameters_json)
                for i, p in enumerate(params):
                    if p.get('name'):
                        param = LogsheetScheduleParameter(
                            schedule_id=schedule.id,
                            name=p['name'],
                            entry_type=p.get('entry_type', 'reading'),
                            unit=p.get('unit', ''),
                            standard_min=float(p['min']) if p.get('min') else None,
                            standard_max=float(p['max']) if p.get('max') else None,
                            position=i
                        )
                        db.session.add(param)
            except:
                pass

            db.session.commit()
            flash(f'Jadwal {code} berhasil dibuat', 'success')
            return redirect(url_for('logsheet_management', tab='schedules'))

        # GET: Show create form
        from datetime import date
        from models import Site
        
        if current_user.site_id:
            assets = Asset.query.filter_by(status='Online', site_id=current_user.site_id).all()
            users = User.query.filter(User.role.in_(['Technician', 'Supervisor', 'Admin']), User.site_id == current_user.site_id).all()
            sites = Site.query.filter_by(id=current_user.site_id).all()
        else:
            assets = Asset.query.filter_by(status='Online').all()
            users = User.query.filter(User.role.in_(['Technician', 'Supervisor', 'Admin'])).all()
            sites = Site.query.all()
            
        from models import LogsheetTemplate, Checklist
        logsheet_templates = LogsheetTemplate.query.order_by(LogsheetTemplate.name).all()
        
        if current_user.site_id:
            user_site = Site.query.get(current_user.site_id)
            if user_site and user_site.project_code:
                checklists = Checklist.query.filter(db.or_(Checklist.project_code == user_site.project_code, Checklist.project_code == None, Checklist.project_code == '')).order_by(Checklist.name).all()
            else:
                checklists = Checklist.query.filter(db.or_(Checklist.project_code == None, Checklist.project_code == '')).order_by(Checklist.name).all()
        else:
            checklists = Checklist.query.order_by(Checklist.name).all()
            
        for c in checklists:
            c.project_code_group = c.project_code if c.project_code else ""
            
        return render_template('dashboard/logsheet_schedule_create.html', assets=assets, users=users, sites=sites, today=date.today(), logsheet_templates=logsheet_templates, checklists=checklists)

    @app.route('/dashboard/logsheet/schedule/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def logsheet_schedule_edit(id):
        """Edit an existing logsheet schedule"""
        if current_user.role not in ['Admin', 'Supervisor']:
            flash('Unauthorized', 'danger')
            return redirect(url_for('logsheet_management', tab='schedules'))
            
        from models import LogsheetSchedule, LogsheetScheduleParameter, User, Site
        from datetime import date, time
        import json
        
        schedule = LogsheetSchedule.query.get_or_404(id)
        
        if request.method == 'POST':
            name = request.form.get('name')
            asset_id = request.form.get('asset_id')
            scheduled_date = request.form.get('scheduled_date')
            scheduled_time = request.form.get('scheduled_time', '08:00')
            techs_raw = request.form.get('technicians', '')
            assigned_technicians = techs_raw.split(',') if techs_raw else []
            parameters_json = request.form.get('parameters_json', '[]')
            form_site_id = request.form.get('site_id')

            if not name or not asset_id or not scheduled_date:
                flash('Mohon lengkapi semua field wajib', 'warning')
                return redirect(url_for('logsheet_schedule_edit', id=id))

            schedule.name = name
            schedule.asset_id = asset_id
            schedule.scheduled_date = date.fromisoformat(scheduled_date)
            
            try:
                schedule.scheduled_time = time.fromisoformat(scheduled_time) if scheduled_time else None
            except:
                pass
                
            if form_site_id:
                schedule.site_id = int(form_site_id)

            # Update technicians
            schedule.assigned_technicians = []
            for tech_id in assigned_technicians:
                tech = User.query.get(int(tech_id))
                if tech:
                    schedule.assigned_technicians.append(tech)

            # Update parameters (delete old, add new)
            LogsheetScheduleParameter.query.filter_by(schedule_id=schedule.id).delete()
            try:
                params = json.loads(parameters_json)
                for i, p in enumerate(params):
                    if p.get('name'):
                        param = LogsheetScheduleParameter(
                            schedule_id=schedule.id,
                            name=p['name'],
                            entry_type=p.get('entry_type', 'reading'),
                            unit=p.get('unit', ''),
                            standard_min=float(p['min']) if p.get('min') else None,
                            standard_max=float(p['max']) if p.get('max') else None,
                            position=i
                        )
                        db.session.add(param)
            except:
                pass

            db.session.commit()
            flash(f'Jadwal {schedule.code} berhasil diperbarui', 'success')
            return redirect(url_for('logsheet_management', tab='schedules'))

        if current_user.site_id:
            assets = Asset.query.filter_by(status='Online', site_id=current_user.site_id).all()
            users = User.query.filter(User.role.in_(['Technician', 'Supervisor', 'Admin']), User.site_id == current_user.site_id).all()
            sites = Site.query.filter_by(id=current_user.site_id).all()
        else:
            assets = Asset.query.filter_by(status='Online').all()
            users = User.query.filter(User.role.in_(['Technician', 'Supervisor', 'Admin'])).all()
            sites = Site.query.all()
            
        # Serialize existing parameters for frontend
        existing_params = []
        for p in schedule.parameters:
            existing_params.append({
                'name': p.name,
                'entry_type': p.entry_type,
                'unit': p.unit or '',
                'min': p.standard_min if p.standard_min is not None else '',
                'max': p.standard_max if p.standard_max is not None else ''
            })
            
        # Extract existing tech IDs
        existing_tech_ids = [str(t.id) for t in schedule.assigned_technicians]
        
        from models import LogsheetTemplate, Checklist
        logsheet_templates = LogsheetTemplate.query.order_by(LogsheetTemplate.name).all()
        
        if current_user.site_id:
            user_site = Site.query.get(current_user.site_id)
            if user_site and user_site.project_code:
                checklists = Checklist.query.filter(db.or_(Checklist.project_code == user_site.project_code, Checklist.project_code == None, Checklist.project_code == '')).order_by(Checklist.name).all()
            else:
                checklists = Checklist.query.filter(db.or_(Checklist.project_code == None, Checklist.project_code == '')).order_by(Checklist.name).all()
        else:
            checklists = Checklist.query.order_by(Checklist.name).all()
            
        for c in checklists:
            c.project_code_group = c.project_code if c.project_code else ""
            
        return render_template('dashboard/logsheet_schedule_edit.html', 
                             schedule=schedule,
                             assets=assets, 
                             users=users, 
                             sites=sites,
                             existing_params_json=json.dumps(existing_params),
                             existing_tech_ids=','.join(existing_tech_ids),
                             logsheet_templates=logsheet_templates,
                             checklists=checklists)

    @app.route('/dashboard/logsheet/schedule/<int:id>/execute', methods=['GET', 'POST'])
    @login_required
    def logsheet_schedule_execute(id):
        """Execute a schedule - create the actual logsheet"""
        from models import LogsheetSchedule, LogsheetScheduleParameter, Logsheet, LogsheetEntry
        from datetime import datetime, date

        schedule = LogsheetSchedule.query.get_or_404(id)

        # Check if user is assigned
        if current_user not in schedule.assigned_technicians and current_user.role not in ['Admin', 'Supervisor']:
            flash('Anda tidak ditugaskan untuk jadwal ini', 'danger')
            return redirect(url_for('logsheet_management', tab='schedules'))

        # Check if logsheet already exists
        if schedule.logsheet:
            return redirect(url_for('logsheet_fill', id=schedule.logsheet.id))

        if request.method == 'POST':
            if request.form.get('action') == 'add_param':
                new_param_name = request.form.get('new_param_name')
                new_param_unit = request.form.get('new_param_unit')
                new_param_type = request.form.get('new_param_type', 'reading')
                
                from models import AssetMeter
                
                # Add to LogsheetScheduleParameter
                new_param = LogsheetScheduleParameter(
                    schedule_id=schedule.id,
                    name=new_param_name,
                    unit=new_param_unit,
                    entry_type=new_param_type
                )
                db.session.add(new_param)
                
                # Add to AssetMeter if it's an asset schedule
                if schedule.asset_id:
                    meter = AssetMeter(
                        asset_id=schedule.asset_id,
                        name=new_param_name,
                        unit=new_param_unit
                    )
                    db.session.add(meter)
                    
                db.session.commit()
                flash('Parameter baru berhasil ditambahkan ke jadwal dan master metering!', 'success')
                return redirect(url_for('logsheet_schedule_execute', id=schedule.id))
                
            if request.form.get('action') == 'pull_meters':
                if schedule.asset_id:
                    from models import AssetMeter, AssetCustomField
                    import requests
                    
                    added_count = 0
                    
                    # 1. Pull from AssetMeter table
                    meters = AssetMeter.query.filter_by(asset_id=schedule.asset_id).all()
                    for meter in meters:
                        existing = LogsheetScheduleParameter.query.filter_by(schedule_id=schedule.id, name=meter.name).first()
                        if not existing:
                            new_param = LogsheetScheduleParameter(
                                schedule_id=schedule.id,
                                name=meter.name,
                                unit=meter.unit,
                                entry_type='reading'
                            )
                            db.session.add(new_param)
                            added_count += 1
                            
                    # 2. Pull from external IoT API if configured
                    cf = AssetCustomField.query.filter_by(asset_id=schedule.asset_id, field_name='IoT API URL').first()
                    if cf and cf.field_value:
                        try:
                            resp = requests.get(cf.field_value, timeout=10)
                            if resp.status_code == 200:
                                data = resp.json()
                                
                                def extract_metrics(d, prefix=''):
                                    m = {}
                                    if isinstance(d, dict):
                                        for k, v in d.items():
                                            if isinstance(v, list): continue
                                            new_prefix = f"{prefix}.{k}" if prefix else k
                                            if isinstance(v, (int, float)):
                                                m[new_prefix] = v
                                            elif isinstance(v, dict):
                                                m.update(extract_metrics(v, new_prefix))
                                    return m
                                
                                latest = data
                                if isinstance(data, list) and len(data) > 0:
                                    latest = data[0]
                                elif isinstance(data, dict):
                                    for v in data.values():
                                        if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                                            latest = v[0]
                                            break
                                            
                                metrics = extract_metrics(latest)
                                for metric_name in metrics.keys():
                                    display_name = metric_name.replace('_', ' ').upper()
                                    display_name = display_name.replace('PARSED DATA.', '')
                                    
                                    existing = LogsheetScheduleParameter.query.filter_by(schedule_id=schedule.id, name=display_name).first()
                                    if not existing:
                                        new_param = LogsheetScheduleParameter(
                                            schedule_id=schedule.id,
                                            name=display_name,
                                            unit='',
                                            entry_type='reading'
                                        )
                                        db.session.add(new_param)
                                        added_count += 1
                                        
                                # Clean up any existing parameters that might have 'PARSED DATA.' prefix from previous pulls
                                for p in LogsheetScheduleParameter.query.filter_by(schedule_id=schedule.id).all():
                                    if 'PARSED DATA.' in p.name:
                                        clean_name = p.name.replace('PARSED DATA.', '')
                                        if not LogsheetScheduleParameter.query.filter_by(schedule_id=schedule.id, name=clean_name).first():
                                            p.name = clean_name
                                        else:
                                            db.session.delete(p)
                        except Exception as e:
                            print(f"Error fetching IoT API: {e}")
                    
                    if added_count > 0:
                        db.session.commit()
                        flash(f'Berhasil menarik {added_count} parameter dari API Metering & Live IoT!', 'success')
                    else:
                        flash('Semua parameter sudah ada di daftar atau tidak ada metering yang tersedia.', 'info')
                else:
                    flash('Jadwal ini tidak terhubung dengan aset.', 'warning')
                return redirect(url_for('logsheet_schedule_execute', id=schedule.id))

            notes = request.form.get('notes', '')
            entries_data = request.form.get('entries_json', '[]')
            
            # Generate LS code
            today = date.today()
            date_str = today.strftime('%Y%m%d')
            count = Logsheet.query.filter(Logsheet.code.like(f'LS-{date_str}-%')).count()
            code = f"LS-{date_str}-{str(count + 1).zfill(3)}"

            # Create logsheet
            logsheet = Logsheet(
                code=code,
                schedule_id=schedule.id,
                date=schedule.scheduled_date,
                status='Draft',
                asset_id=schedule.asset_id,
                site_id=schedule.site_id,
                filled_by_id=current_user.id,
                notes=notes
            )
            db.session.add(logsheet)
            db.session.flush()

            # Log activity
            from models import LogsheetLog
            new_log = LogsheetLog(
                logsheet_id=logsheet.id,
                user_id=current_user.id,
                action='Dibuat',
                note=f'Logsheet dibuat dari schedule: {schedule.name}'
            )
            db.session.add(new_log)

            # Add entries from schedule parameters
            import json
            try:
                entries = json.loads(entries_data)
                for e in entries:
                    entry = LogsheetEntry(
                        logsheet_id=logsheet.id,
                        entry_type=e.get('entry_type', 'reading'),
                        parameter_name=e.get('parameter_name', ''),
                        unit=e.get('unit', ''),
                        value=e.get('value', ''),
                        standard_min=float(e['min']) if e.get('min') else None,
                        standard_max=float(e['max']) if e.get('max') else None,
                        description=e.get('description', ''),
                        is_completed=e.get('is_completed', False),
                        position=e.get('position', 0)
                    )
                    db.session.add(entry)
            except:
                pass

            # Update schedule status
            schedule.status = 'In Progress'

            db.session.commit()
            flash(f'Logsheet {code} berhasil dibuat', 'success')
            return redirect(url_for('logsheet_fill', id=logsheet.id))

        # Load parameters
        parameters = LogsheetScheduleParameter.query.filter_by(schedule_id=id).order_by(LogsheetScheduleParameter.position).all()
        
        # Check for IoT API to enable auto-fill
        iot_api_url = None
        if schedule.asset_id:
            from models import AssetCustomField
            cf = AssetCustomField.query.filter_by(asset_id=schedule.asset_id, field_name='IoT API URL').first()
            if cf:
                iot_api_url = cf.field_value

        return render_template('dashboard/logsheet_schedule_execute.html',
                            schedule=schedule, parameters=parameters, iot_api_url=iot_api_url)

    @app.route('/dashboard/logsheet/schedule/<int:id>/delete', methods=['POST'])
    @login_required
    def logsheet_schedule_delete(id):
        """Delete a schedule"""
        if current_user.role not in ['Admin', 'Supervisor']:
            flash('Unauthorized', 'danger')
            return redirect(url_for('logsheet_management', tab='schedules'))
            
        from models import LogsheetSchedule
        schedule = LogsheetSchedule.query.get_or_404(id)
        db.session.delete(schedule)
        db.session.commit()
        flash('Jadwal berhasil dihapus', 'success')
        return redirect(url_for('logsheet_management', tab='schedules'))

    @app.route('/dashboard/logsheet/<int:id>/delete', methods=['POST'])
    @login_required
    def logsheet_delete(id):
        """Delete a filled logsheet (record)"""
        if current_user.role not in ['Admin', 'Supervisor']:
            flash('Unauthorized', 'danger')
            return redirect(url_for('logsheet_management', tab='records'))
            
        from models import Logsheet
        ls = Logsheet.query.get_or_404(id)
        
        # Free up the schedule if it was completed by this logsheet
        if ls.logsheet_schedule:
            ls.logsheet_schedule.status = 'Scheduled'
            
        db.session.delete(ls)
        db.session.commit()
        flash('Logsheet record berhasil dihapus', 'success')
        return redirect(url_for('logsheet_management', tab='records'))

    # ============================================
    # LOGSHEET ROUTES - For Technicians
    # ============================================
    @app.route('/dashboard/logsheet/my-tasks')
    @login_required
    def logsheet_my_tasks():
        """Show logsheet tasks assigned to current user"""
        from models import LogsheetSchedule, logsheet_schedule_technicians
        from sqlalchemy.orm import selectinload
        from datetime import date

        today = date.today()

        # Get schedules assigned to current user
        my_schedules = LogsheetSchedule.query.join(
            logsheet_schedule_technicians
        ).filter(
            logsheet_schedule_technicians.c.user_id == current_user.id
        ).options(
            selectinload(LogsheetSchedule.asset),
            selectinload(LogsheetSchedule.site),
            selectinload(LogsheetSchedule.logsheet)
        ).order_by(LogsheetSchedule.scheduled_date.desc()).all()

        return render_template('dashboard/logsheet_my_tasks.html',
                            schedules=my_schedules, today=today)



    @app.route('/dashboard/logsheet/<int:id>/fill', methods=['GET', 'POST'])
    @login_required
    def logsheet_fill(id):
        """Fill/edit a logsheet"""
        from models import Logsheet, LogsheetEntry
        from sqlalchemy.orm import selectinload
        from datetime import datetime

        logsheet = Logsheet.query.options(
            selectinload(Logsheet.logsheet_schedule)
        ).get_or_404(id)

        # Check permission
        if logsheet.filled_by_id != current_user.id and current_user.role not in ['Admin', 'Supervisor']:
            flash('Anda tidak memiliki akses ke logsheet ini', 'danger')
            return redirect(url_for('logsheet_list'))

        if request.method == 'POST':
            logsheet.notes = request.form.get('notes', '')

            # Update entries
            entries_data = request.form.get('entries_json', '[]')
            import json
            try:
                entries = json.loads(entries_data)
                for e in entries:
                    if e.get('id'):
                        entry = LogsheetEntry.query.get(int(e['id']))
                        if entry:
                            entry.value = e.get('value', '')
                            entry.is_completed = e.get('is_completed', False)
                            entry.description = e.get('description', '')
            except:
                pass

            if logsheet.status != 'Submitted':
                logsheet.status = 'Submitted'
                logsheet.submitted_at = datetime.utcnow()
                if logsheet.logsheet_schedule:
                    logsheet.logsheet_schedule.status = 'Completed'
                    logsheet.logsheet_schedule.completed_at = datetime.utcnow()
                
                from models import LogsheetLog
                new_log = LogsheetLog(
                    logsheet_id=logsheet.id,
                    user_id=current_user.id,
                    action='Submitted',
                    note='Logsheet di-submit untuk verifikasi Supervisor'
                )
                db.session.add(new_log)

                # Connect to Asset Metering automatically upon save
                from models import AssetMeter, AssetMeterReading
                for entry in logsheet.entries:
                    if entry.entry_type == 'reading' and entry.value:
                        try:
                            # Attempt to parse as float
                            val = float(entry.value)
                            
                            # Find existing meter
                            meter = AssetMeter.query.filter_by(
                                asset_id=logsheet.asset_id,
                                name=entry.parameter_name
                            ).first()
                            
                            # Create if it doesn't exist
                            if not meter:
                                meter = AssetMeter(
                                    asset_id=logsheet.asset_id,
                                    name=entry.parameter_name,
                                    unit=entry.unit
                                )
                                db.session.add(meter)
                                db.session.flush() # Get meter.id
                                
                            # Add reading
                            reading = AssetMeterReading(
                                meter_id=meter.id,
                                reading_value=val,
                                reading_date=logsheet.submitted_at or datetime.utcnow(),
                                user_id=current_user.id
                            )
                            db.session.add(reading)
                        except ValueError:
                            # Skip if value is not a valid number
                            pass

                db.session.commit()
                flash('Logsheet berhasil di-submit untuk verifikasi Supervisor', 'success')
            else:
                db.session.commit()
                flash('Parameter berhasil diperbarui', 'success')
            return redirect(url_for('logsheet_detail', id=id))

        entries = LogsheetEntry.query.filter_by(logsheet_id=id).order_by(LogsheetEntry.position).all()

        return render_template('dashboard/logsheet_fill.html', logsheet=logsheet, entries=entries)

    @app.route('/dashboard/logsheet/<int:id>/export_pdf', methods=['GET'])
    @login_required
    def logsheet_export_pdf(id):
        """Export logsheet to PDF"""
        import os
        from fpdf import FPDF
        from models import Logsheet
        from datetime import datetime
        from flask import make_response, current_app, redirect, flash, url_for

        logsheet = Logsheet.query.get_or_404(id)
        
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # --- 0. COVER PAGE ---
        pdf.add_page()
        
        # Background Image
        title_image_path = os.path.join(current_app.root_path, 'static', 'images', 'judul.png')
        if os.path.exists(title_image_path):
            pdf.image(title_image_path, x=0, y=0, w=pdf.w, h=pdf.h)
        
        # Get Site Name and Period
        site_name = logsheet.site.name if logsheet.site else "Unknown Site"
        ls_date = logsheet.date or datetime.now()
        month_map = {
            1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL", 5: "MEI", 6: "JUNI",
            7: "JULI", 8: "AGUSTUS", 9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER"
        }
        
        line1 = f"LAPORAN LOGSHEET"
        line1_sub = "MAINTENANCE"
        line2 = f"{site_name.upper()}"
        line3 = f"{logsheet.asset.name.upper() if logsheet.asset else ''}"
        line4 = f"{logsheet.code}"
        
        # Positioning text at bottom left
        pdf.set_y(-105)
        pdf.set_left_margin(20)
        
        pdf.set_font('helvetica', 'B', 24)
        pdf.cell(0, 12, line1, 0, 1, 'L')
        pdf.set_font('helvetica', 'B', 24)
        pdf.cell(0, 12, line1_sub, 0, 1, 'L')
        
        pdf.set_font('helvetica', 'B', 18)
        pdf.cell(0, 10, line2, 0, 1, 'L')
        
        pdf.set_font('helvetica', 'B', 18)
        pdf.cell(0, 10, line3, 0, 1, 'L')
        
        pdf.set_font('helvetica', 'B', 18)
        pdf.cell(0, 10, line4, 0, 1, 'L')
        
        # Reset for main report
        pdf.set_left_margin(10)
        pdf.add_page()
        # --- END COVER PAGE ---
        
        try:
            pdf.set_font("helvetica", style="B", size=10)
        except:
            pdf.set_font("Arial", style="B", size=10)
            
        start_x = pdf.get_x()
        start_y = pdf.get_y()
        
        # 1. NEW HEADER
        pdf.cell(35, 24, "", border=1) # Logo area box
        
        logo_path = os.path.join(current_app.root_path, 'static', 'images', 'Logo Jaya Teknik.png')
        if os.path.exists(logo_path):
            try:
                pdf.image(logo_path, x=start_x + 2, y=start_y + 2, w=31)
            except:
                pass
        
        # Title
        pdf.set_font("helvetica", style="B", size=14)
        pdf.set_xy(start_x + 35, start_y)
        pdf.cell(105, 24, "", border=1)
       
        pdf.set_xy(start_x + 35, start_y + 12)
        pdf.cell(105, 8, "REPORT LOGSHEET", align="C")
        
        # Info box right
        pdf.set_font("helvetica", size=8)
        pdf.set_xy(start_x + 140, start_y)
        pdf.cell(20, 6, "No.Dok", border=1)
        pdf.cell(30, 6, "RP - JT - 26", border=1)
        
        pdf.set_xy(start_x + 140, start_y + 6)
        pdf.cell(20, 6, "Ref.", border=1)
        pdf.cell(30, 6, "7; 7.1.3 & 7.1.4", border=1)
        
        pdf.set_xy(start_x + 140, start_y + 12)
        pdf.cell(20, 6, "Rev.", border=1)
        pdf.cell(30, 6, "Original", border=1)
        
        pdf.set_xy(start_x + 140, start_y + 18)
        pdf.cell(20, 6, "Tanggal", border=1)
        printed_date = datetime.now().strftime("%d %b %Y")
        pdf.cell(30, 6, printed_date, border=1)
        
        # Details Body
        pdf.set_xy(start_x, start_y + 24)
        pdf.set_font("helvetica", size=9)
        pdf.cell(190, 24, "", border=1)
        pdf.set_xy(start_x, start_y + 24)
        
        def fmt_dt(dt):
            if not dt: return '-'
            if isinstance(dt, datetime): return dt.strftime('%d-%m-%Y %H:%M')
            return dt.strftime('%d-%m-%Y')
            
        nomor_val = logsheet.code or '-'
        asset_val = f"{logsheet.asset.name} ({logsheet.asset.code})" if logsheet.asset else '-'
        resp_val = logsheet.filled_by.name if logsheet.filled_by else "N/A"
        
        proj_val = (logsheet.asset.project_code if logsheet.asset and logsheet.asset.project_code else "-") or '-'
        
        loc_val = '-'
        if logsheet.asset and hasattr(logsheet.asset, 'location') and logsheet.asset.location:
            loc_val = logsheet.asset.location.name if hasattr(logsheet.asset.location, 'name') else str(logsheet.asset.location)
        
        act_val = fmt_dt(logsheet.date)
        
        # Line 1
        pdf.cell(20, 6, "Form", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, "LOGSHEET", border=0)
        pdf.cell(20, 6, "Project", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(proj_val)[:35], border=0, ln=1)
        
        # Line 2
        pdf.cell(20, 6, "Nomor", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(nomor_val)[:35], border=0)
        pdf.cell(20, 6, "Location", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(loc_val)[:35], border=0, ln=1)
        
        # Line 3
        pdf.cell(20, 6, "Asset", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(asset_val)[:35], border=0)
        pdf.cell(20, 6, "Date", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(act_val)[:40], border=0, ln=1)
        
        # Line 4
        pdf.cell(20, 6, "Responsible", border=0)
        pdf.cell(5, 6, ":", border=0)
        pdf.cell(70, 6, str(resp_val)[:35], border=0, ln=1)
        
        pdf.ln(5)
        
        # 1.5 TECHNICIAN
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("helvetica", style="B", size=10)
        pdf.cell(190, 6, "TECHNICIAN", border=1, align="C", fill=True, ln=1)
        pdf.cell(190, 6, "Name", border=1, align="C", fill=True, ln=1)
        pdf.set_font("helvetica", size=9)
        pdf.cell(190, 6, str(resp_val), border=1, align="L", ln=1)
        pdf.ln(5)
        
        # 2. CHECKING REPORT
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("helvetica", style="B", size=10)
        pdf.cell(190, 6, "CHECKING REPORT", border=1, align="C", fill=True, ln=1)
        
        pdf.set_font("helvetica", style="B", size=8)
        pdf.cell(75, 8, "Description (Unit Check)", border=1, align="C", fill=True)
        pdf.cell(25, 8, "Standard", border=1, align="C", fill=True)
        pdf.cell(25, 8, "Actual", border=1, align="C", fill=True)
        pdf.cell(25, 8, "Check", border=1, align="C", fill=True)
        pdf.cell(40, 8, "Note", border=1, align="C", fill=True, ln=1)
        
        pdf.set_font("helvetica", size=8)
        for entry in logsheet.entries:
            desc = (entry.parameter_name[:40] + '...') if entry.parameter_name and len(entry.parameter_name) > 42 else (entry.parameter_name or entry.description or '-')
            pdf.cell(75, 6, str(desc), border=1)
            
            std_val = "-"
            if entry.standard_min is not None and entry.standard_max is not None:
                std_val = f"{entry.standard_min} - {entry.standard_max}"
            elif entry.standard_min is not None:
                std_val = f">= {entry.standard_min}"
            elif entry.standard_max is not None:
                std_val = f"<= {entry.standard_max}"
                
            pdf.cell(25, 6, str(std_val)[:15], border=1, align="C")
            
            actual_val = str(entry.value) if entry.value else "-"
            pdf.cell(25, 6, actual_val[:15], border=1, align="C")
            
            check_val = "OK"
            if entry.entry_type == 'task' or entry.entry_type == 'observation':
                check_val = "v" if entry.is_completed else "-"
            elif actual_val != "-":
                check_val = "v"
            else:
                check_val = "-"
                
            pdf.cell(25, 6, "OK" if check_val == "v" else "-", border=1, align="C")
            
            note_val = str(entry.description) if entry.description and entry.entry_type != 'task' else ""
            pdf.cell(40, 6, note_val[:20], border=1, ln=1)
        
        pdf.ln(5)
        
        # 3. WORK LOGS / ACTIVITY (Notes in Logsheet)
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("helvetica", style="B", size=10)
        pdf.cell(190, 6, "NOTES", border=1, align="C", fill=True, ln=1)
        pdf.set_font("helvetica", size=8)
        if not logsheet.notes:
            pdf.cell(190, 6, "No notes recorded.", border=1, align="C", ln=1)
        else:
            pdf.multi_cell(190, 6, logsheet.notes, border=1)
                
        pdf.ln(5)
        
        # 3.6 SIGNATURES
        pdf.ln(5)
        
        first_tech = logsheet.filled_by
        tech_name = first_tech.name if first_tech else "....."
        tech_role = first_tech.role if first_tech else "....."
        site_name = logsheet.site.name.upper() if logsheet.site else "....."
        
        if pdf.get_y() > 240:
            pdf.add_page()
            
        sig_y = pdf.get_y()
        
        c_name_print = "....."
        c_title_print = "....."
        
        # Right Column (Pihak Kedua)
        pdf.set_xy(110, sig_y)
        pdf.set_font("helvetica", style="B", size=9)
        pdf.cell(85, 5, "PELAKSANA,", ln=1)
        pdf.set_x(110)
        pdf.cell(85, 5, "PT JAYA TEKNIK INDONESIA", ln=1)
        
        # Add technician signature if exists in LogsheetSignature
        import tempfile
        import base64
        def save_temp_image(b64_str):
            if not b64_str or ',' not in b64_str: return None
            try:
                _, encoded = b64_str.split(",", 1)
                data = base64.b64decode(encoded)
                fd, temp_path = tempfile.mkstemp(suffix='.png')
                with os.fdopen(fd, 'wb') as f:
                    f.write(data)
                return temp_path
            except:
                return None

        # Operator Signature
        op_sig = next((s for s in logsheet.signatures if s.signature_type == 'operator'), None)
        if op_sig and op_sig.signature_data:
            t_img_path = save_temp_image(op_sig.signature_data)
            if t_img_path:
                try:
                    pdf.image(t_img_path, x=110, y=sig_y + 10, h=14)
                    os.remove(t_img_path)
                except: pass
                if op_sig.signed_name:
                    tech_name = op_sig.signed_name

        pdf.set_xy(110, sig_y + 25)
        pdf.set_font("helvetica", size=9)
        pdf.cell(85, 5, f"Nama : {tech_name}", ln=1)
        pdf.set_x(110)
        pdf.cell(85, 5, f"Jabatan : {tech_role}", ln=1)
        
        # Left Column (Pihak Pertama)
        pdf.set_xy(15, sig_y)
        pdf.set_font("helvetica", style="B", size=9)
        pdf.cell(90, 5, "DIKETAHUI OLEH,", ln=1)
        pdf.set_x(15)
        pdf.cell(90, 5, site_name, ln=1)
        
        sup_sig = next((s for s in logsheet.signatures if s.signature_type == 'supervisor'), None)
        if sup_sig and sup_sig.signature_data:
            c_img_path = save_temp_image(sup_sig.signature_data)
            if c_img_path:
                try:
                    pdf.image(c_img_path, x=15, y=sig_y + 10, h=14)
                    os.remove(c_img_path)
                except: pass
                if sup_sig.signed_name:
                    c_name_print = sup_sig.signed_name

        pdf.set_xy(15, sig_y + 25)
        pdf.set_font("helvetica", size=9)
        pdf.cell(90, 5, f"Nama : {c_name_print}", ln=1)
        pdf.set_x(15)
        pdf.cell(90, 5, f"Jabatan : {c_title_print}", ln=1)
        
        try:
            out = pdf.output(dest='S')
        except TypeError:
            out = pdf.output()
        pdf_bytes = out.encode('latin-1') if isinstance(out, str) else bytes(out)
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=logsheet_{logsheet.code}.pdf'
        return response

    @app.route('/dashboard/logsheet/<int:id>', methods=['GET'])
    @login_required
    def logsheet_detail(id):
        """View a specific logsheet"""
        from models import Logsheet
        from sqlalchemy.orm import selectinload
        from datetime import datetime

        logsheet = Logsheet.query.options(
            selectinload(Logsheet.asset),
            selectinload(Logsheet.site),
            selectinload(Logsheet.filled_by),
            selectinload(Logsheet.logsheet_schedule)
        ).get_or_404(id)

        now = datetime.now()

        return render_template('dashboard/logsheet_detail.html', logsheet=logsheet, now=now)

    @app.route('/dashboard/logsheet/<int:id>/submit', methods=['POST'])
    @login_required
    def logsheet_submit(id):
        """Submit a logsheet for approval"""
        from models import Logsheet, LogsheetSchedule, AssetMeter, AssetMeterReading, LogsheetLog
        from datetime import datetime

        logsheet = Logsheet.query.get_or_404(id)
        logsheet.status = 'Submitted'
        logsheet.submitted_at = datetime.utcnow()
        
        new_log = LogsheetLog(
            logsheet_id=logsheet.id,
            user_id=current_user.id,
            action='Submitted',
            note='Logsheet di-submit untuk verifikasi Supervisor'
        )
        db.session.add(new_log)

        # Update schedule status
        if logsheet.logsheet_schedule:
            logsheet.logsheet_schedule.status = 'Completed'
            logsheet.logsheet_schedule.completed_at = datetime.utcnow()

        # Connect to Asset Metering
        for entry in logsheet.entries:
            if entry.entry_type == 'reading' and entry.value:
                try:
                    # Attempt to parse as float
                    val = float(entry.value)
                    
                    # Find existing meter
                    meter = AssetMeter.query.filter_by(
                        asset_id=logsheet.asset_id,
                        name=entry.parameter_name
                    ).first()
                    
                    # Create if it doesn't exist
                    if not meter:
                        meter = AssetMeter(
                            asset_id=logsheet.asset_id,
                            name=entry.parameter_name,
                            unit=entry.unit
                        )
                        db.session.add(meter)
                        db.session.flush() # Get meter.id
                        
                    # Add reading
                    reading = AssetMeterReading(
                        meter_id=meter.id,
                        reading_value=val,
                        reading_date=logsheet.submitted_at,
                        user_id=current_user.id
                    )
                    db.session.add(reading)
                except ValueError:
                    # Skip if value is not a valid number
                    pass

        db.session.commit()
        flash(f'Logsheet {logsheet.code} berhasil disubmit', 'success')
        return redirect(url_for('logsheet_detail', id=id))

    @app.route('/dashboard/logsheet/<int:id>/save-signatures', methods=['POST'])
    @login_required
    def logsheet_save_signatures(id):
        from models import Logsheet, LogsheetSignature
        from datetime import datetime
        logsheet = Logsheet.query.get_or_404(id)
        
        # Save Operator Signature
        op_sig = request.form.get('operator_signature')
        op_name = request.form.get('operator_name')
        if op_sig:
            sig = logsheet.signatures.filter_by(signature_type='operator').first()
            if not sig:
                sig = LogsheetSignature(logsheet_id=id, signature_type='operator')
                db.session.add(sig)
            sig.signature_data = op_sig
            sig.signed_name = op_name
            sig.signed_at = datetime.utcnow()
            sig.user_id = current_user.id

        # Save Supervisor Signature
        sup_sig = request.form.get('supervisor_signature')
        sup_name = request.form.get('supervisor_name')
        if sup_sig:
            sig = logsheet.signatures.filter_by(signature_type='supervisor').first()
            if not sig:
                sig = LogsheetSignature(logsheet_id=id, signature_type='supervisor')
                db.session.add(sig)
            sig.signature_data = sup_sig
            sig.signed_name = sup_name
            sig.signed_at = datetime.utcnow()
            sig.user_id = current_user.id
            
        db.session.commit()
        flash(f'Signatures for {logsheet.code} saved successfully.', 'success')
        return redirect(url_for('logsheet_detail', id=id) + '#signature')

    @app.route('/dashboard/logsheet/<int:id>/approve', methods=['POST'])
    @login_required
    def logsheet_approve(id):
        """Approve a logsheet"""
        from models import Logsheet, LogsheetLog
        from datetime import datetime

        logsheet = Logsheet.query.get_or_404(id)
        logsheet.status = 'Approved'
        logsheet.approved_at = datetime.utcnow()
        
        new_log = LogsheetLog(
            logsheet_id=logsheet.id,
            user_id=current_user.id,
            action='Verified',
            note='Logsheet diverifikasi oleh Supervisor'
        )
        db.session.add(new_log)
        
        db.session.commit()
        flash(f'Logsheet {logsheet.code} berhasil diapprove', 'success')
        return redirect(url_for('logsheet_detail', id=id))

    @app.route('/api/logsheet/entry/<int:id>', methods=['POST'])
    @login_required
    def logsheet_update_entry(id):
        """Update a logsheet entry via API"""
        from models import LogsheetEntry

        entry = LogsheetEntry.query.get_or_404(id)
        data = request.get_json()

        if 'value' in data:
            entry.value = data['value']
        if 'is_completed' in data:
            entry.is_completed = data['is_completed']
        if 'notes' in data:
            entry.notes = data['notes']

        db.session.commit()

        return jsonify({'success': True})

    @app.route('/api/logsheet/<int:id>/entry', methods=['POST'])
    @login_required
    def logsheet_add_entry(id):
        """Add a new entry to logsheet"""
        from models import Logsheet, LogsheetEntry

        logsheet = Logsheet.query.get_or_404(id)
        data = request.get_json()

        entry = LogsheetEntry(
            logsheet_id=id,
            entry_type=data.get('entry_type', 'observation'),
            parameter_name=data.get('parameter_name', ''),
            unit=data.get('unit', ''),
            description=data.get('description', ''),
            position=logsheet.entries.count()
        )
        db.session.add(entry)
        db.session.commit()

        return jsonify({'success': True, 'entry_id': entry.id})

    # ============================================
    # Legacy Work Order Routes
    # ============================================

    @app.route('/api/work_order/<int:id>/start', methods=['POST'])
    @login_required
    def start_work_order(id):
        """Start work order progress"""
        wo = WorkOrder.query.get_or_404(id)
        from datetime import datetime

        # Set start date
        wo.start_date = datetime.now()

        # Find the appropriate status
        in_progress_status = WorkOrderStatus.query.filter_by(name='In Progress').first()
        if in_progress_status:
            wo.current_status_id = in_progress_status.id

        db.session.commit()
        return jsonify({'success': True, 'message': 'Work order started'})

    @app.route('/api/work_order/<int:id>/complete', methods=['POST'])
    @login_required
    def complete_work_order(id):
        """Complete work order"""
        wo = WorkOrder.query.get_or_404(id)
        from datetime import datetime

        # Set end date
        wo.end_date = datetime.now()

        # Find completed status
        completed_status = WorkOrderStatus.query.filter_by(name='Completed').first()
        if completed_status:
            wo.current_status_id = completed_status.id

        db.session.commit()
        return jsonify({'success': True, 'message': 'Work order completed'})

    @app.route('/api/work_order/procedure/<int:proc_id>/toggle', methods=['POST'])
    @login_required
    def toggle_procedure(proc_id):
        """Toggle procedure completion status"""
        from models import WorkOrderProcedure

        proc = WorkOrderProcedure.query.get_or_404(proc_id)
        data = request.get_json()

        proc.is_completed = data.get('completed', False)
        db.session.commit()

        # Calculate completion percentage for the parent WO
        total = proc.work_order.procedures.count()
        completed = proc.work_order.procedures.filter_by(is_completed=True).count()
        completion_percent = round((completed / total) * 100) if total > 0 else 0

        return jsonify({
            'success': True,
            'completion_percent': completion_percent
        })

    # ============================================
    # Dashboard Customization API
    # ============================================
    from flask import jsonify
    
    @app.route('/api/dashboard/layout', methods=['GET'])
    @login_required
    def get_dashboard_layout():
        saved = UserDashboardWidget.query.filter_by(user_id=current_user.id).order_by(UserDashboardWidget.position).all()
        if saved:
            layout = [{'widget_key': w.widget_key, 'position': w.position, 'col_span': w.col_span, 'is_visible': w.is_visible} for w in saved]
        else:
            layout = get_default_layout(current_user.role)
        return jsonify({'layout': layout, 'catalog': get_catalog_for_role(current_user.role)})
    
    @app.route('/api/dashboard/layout', methods=['POST'])
    @login_required
    def save_dashboard_layout():
        data = request.get_json()
        if not data or 'layout' not in data:
            return jsonify({'error': 'Invalid data'}), 400
        
        # Clear current layout
        UserDashboardWidget.query.filter_by(user_id=current_user.id).delete()
        
        for item in data['layout']:
            w = UserDashboardWidget(
                user_id=current_user.id,
                widget_key=item['widget_key'],
                position=item.get('position', 0),
                col_span=item.get('col_span', 6),
                is_visible=item.get('is_visible', True)
            )
            db.session.add(w)
        
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Layout saved successfully'})
    
    @app.route('/api/dashboard/layout/reset', methods=['POST'])
    @login_required
    def reset_dashboard_layout():
        UserDashboardWidget.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Layout reset to default'})
    
    @app.route('/api/dashboard/widget-catalog', methods=['GET'])
    @login_required
    def get_widget_catalog():
        return jsonify({'catalog': get_catalog_for_role(current_user.role)})
    
    # ============================================
    # Custom Sidebar Links API
    # ============================================
    @app.route('/api/sidebar-links', methods=['GET'])
    @login_required
    def get_sidebar_links():
        links = CustomSidebarLink.query.filter_by(user_id=current_user.id).order_by(CustomSidebarLink.position).all()
        return jsonify({'links': [{'id': l.id, 'label': l.label, 'url': l.url, 'icon': l.icon, 'position': l.position} for l in links]})
    
    @app.route('/api/sidebar-links', methods=['POST'])
    @login_required
    def add_sidebar_link():
        data = request.get_json()
        if not data or not data.get('label') or not data.get('url'):
            return jsonify({'error': 'Label and URL are required'}), 400
        
        max_pos = db.session.query(db.func.max(CustomSidebarLink.position)).filter_by(user_id=current_user.id).scalar() or 0
        link = CustomSidebarLink(
            user_id=current_user.id,
            label=data['label'],
            url=data['url'],
            icon=data.get('icon', 'bi-link-45deg'),
            position=max_pos + 1
        )
        db.session.add(link)
        db.session.commit()
        return jsonify({'status': 'ok', 'id': link.id, 'message': 'Link added'})
    
    @app.route('/api/sidebar-links/<int:id>', methods=['DELETE'])
    @login_required
    def delete_sidebar_link(id):
        link = CustomSidebarLink.query.filter_by(id=id, user_id=current_user.id).first()
        if not link:
            return jsonify({'error': 'Link not found'}), 404
        db.session.delete(link)
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Link deleted'})
    

            
    # AUTO-PATCH FORMS FOR CSRF
    import re
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'templates')
    csrf_input = '\n    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>'
    form_tag_re = re.compile(r'(<form[^>]*method=["\']post["\'][^>]*>)', re.IGNORECASE)
    
    def replacer(match):
        return match.group(1) + csrf_input
        
    if os.path.isdir(template_dir):
        for root_dir, dirs, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    filepath = os.path.join(root_dir, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if 'csrf_token()' not in content:
                        new_content = form_tag_re.sub(replacer, content)
                        if new_content != content:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                                
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        try:
            db.create_all() # Create tables if they don't exist
        except Exception as e:
            print(f"Note: db.create_all skipped - {str(e)[:100]}")
            # Tables likely already exist, continue

        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE site ADD COLUMN project_code VARCHAR(50);'))
            db.session.commit()
            print("Successfully auto-migrated site table -> project_code added")
        except Exception as e:
            db.session.rollback()
            pass # column likely already exists
            
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE user ADD COLUMN team_id INTEGER REFERENCES team(id);'))
            db.session.commit()
            print("Successfully auto-migrated user table -> team_id added")
        except Exception as e:
            db.session.rollback()
            pass # column likely already exists
            
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE work_order ADD COLUMN team_id INTEGER REFERENCES team(id);'))
            db.session.commit()
            print("Successfully auto-migrated work_order table -> team_id added")
        except Exception as e:
            db.session.rollback()
            pass
            
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE user ADD COLUMN last_login DATETIME;'))
            db.session.commit()
            print("Successfully auto-migrated user table -> last_login added")
        except Exception as e:
            db.session.rollback()
            pass
            
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE user ADD COLUMN login_count INTEGER DEFAULT 0;'))
            db.session.commit()
            print("Successfully auto-migrated user table -> login_count added")
        except Exception as e:
            db.session.rollback()
            pass
            
        try:
            from sqlalchemy import text
            db.session.execute(text('ALTER TABLE logsheet ADD COLUMN schedule_id INTEGER REFERENCES logsheet_schedule(id);'))
            db.session.commit()
            print("Successfully auto-migrated logsheet table -> schedule_id added")
        except Exception as e:
            db.session.rollback()
            pass

        # Create Logsheet tables if they don't exist
        try:
            from sqlalchemy import text

            # Check if logsheet_schedule table exists
            result = db.session.execute(text("SHOW TABLES LIKE 'logsheet_schedule'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE logsheet_schedule (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        code VARCHAR(50) UNIQUE NOT NULL,
                        scheduled_date DATE NOT NULL,
                        scheduled_time TIME,
                        shift VARCHAR(10),
                        asset_id INT NOT NULL,
                        site_id INT NOT NULL,
                        created_by_id INT NOT NULL,
                        status VARCHAR(20) DEFAULT 'Scheduled',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        completed_at DATETIME,
                        FOREIGN KEY (asset_id) REFERENCES asset(id),
                        FOREIGN KEY (site_id) REFERENCES site(id),
                        FOREIGN KEY (created_by_id) REFERENCES user(id)
                    )
                '''))
                db.session.commit()
                print("Successfully created logsheet_schedule table")

            # Check if logsheet_schedule_technicians table exists
            result = db.session.execute(text("SHOW TABLES LIKE 'logsheet_schedule_technicians'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE logsheet_schedule_technicians (
                        schedule_id INT NOT NULL,
                        user_id INT NOT NULL,
                        PRIMARY KEY (schedule_id, user_id),
                        FOREIGN KEY (schedule_id) REFERENCES logsheet_schedule(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES user(id)
                    )
                '''))
                db.session.commit()
                print("Successfully created logsheet_schedule_technicians table")

            # Check if logsheet_schedule_parameter table exists
            result = db.session.execute(text("SHOW TABLES LIKE 'logsheet_schedule_parameter'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE logsheet_schedule_parameter (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        schedule_id INT NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        entry_type VARCHAR(20) DEFAULT 'reading',
                        unit VARCHAR(20),
                        standard_min FLOAT,
                        standard_max FLOAT,
                        position INT DEFAULT 0,
                        FOREIGN KEY (schedule_id) REFERENCES logsheet_schedule(id) ON DELETE CASCADE
                    )
                '''))
                db.session.commit()
                print("Successfully created logsheet_schedule_parameter table")

            # Check if logsheet table exists (update schema)
            result = db.session.execute(text("SHOW TABLES LIKE 'logsheet'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE logsheet (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        code VARCHAR(50) UNIQUE NOT NULL,
                        schedule_id INT,
                        date DATE NOT NULL,
                        shift VARCHAR(10),
                        status VARCHAR(20) DEFAULT 'Draft',
                        asset_id INT NOT NULL,
                        site_id INT NOT NULL,
                        filled_by_id INT NOT NULL,
                        work_order_id INT,
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        submitted_at DATETIME,
                        approved_at DATETIME,
                        FOREIGN KEY (schedule_id) REFERENCES logsheet_schedule(id),
                        FOREIGN KEY (asset_id) REFERENCES asset(id),
                        FOREIGN KEY (site_id) REFERENCES site(id),
                        FOREIGN KEY (filled_by_id) REFERENCES user(id),
                        FOREIGN KEY (work_order_id) REFERENCES work_order(id)
                    )
                '''))
                db.session.commit()
                print("Successfully created logsheet table")

            # Check if logsheet_entry table exists
            result = db.session.execute(text("SHOW TABLES LIKE 'logsheet_entry'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE logsheet_entry (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        logsheet_id INT NOT NULL,
                        entry_type VARCHAR(30) NOT NULL,
                        parameter_name VARCHAR(100),
                        unit VARCHAR(20),
                        value VARCHAR(100),
                        standard_min FLOAT,
                        standard_max FLOAT,
                        description TEXT,
                        is_completed BOOLEAN DEFAULT FALSE,
                        issue_severity VARCHAR(20),
                        requires_wo BOOLEAN DEFAULT FALSE,
                        position INT DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (logsheet_id) REFERENCES logsheet(id) ON DELETE CASCADE
                    )
                '''))
                db.session.commit()
                print("Successfully created logsheet_entry table")

            # Check if logsheet_signature table exists
            result = db.session.execute(text("SHOW TABLES LIKE 'logsheet_signature'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE logsheet_signature (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        logsheet_id INT NOT NULL,
                        signature_type VARCHAR(30) NOT NULL,
                        user_id INT,
                        signature_data TEXT,
                        signed_name VARCHAR(100),
                        signed_at DATETIME,
                        notes TEXT,
                        FOREIGN KEY (logsheet_id) REFERENCES logsheet(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES user(id)
                    )
                '''))
                db.session.commit()
                print("Successfully created logsheet_signature table")

            # Check if logsheet_log table exists
            result = db.session.execute(text("SHOW TABLES LIKE 'logsheet_log'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE logsheet_log (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        logsheet_id INT NOT NULL,
                        user_id INT NOT NULL,
                        action VARCHAR(100) NOT NULL,
                        note TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (logsheet_id) REFERENCES logsheet(id) ON DELETE CASCADE,
                        FOREIGN KEY (user_id) REFERENCES user(id)
                    )
                '''))
                db.session.commit()
                print("Successfully created logsheet_log table")

            # Check if shift table exists
            result = db.session.execute(text("SHOW TABLES LIKE 'shift'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE shift (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        site_id INT NOT NULL,
                        name VARCHAR(50) NOT NULL,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        FOREIGN KEY (site_id) REFERENCES site(id) ON DELETE CASCADE
                    )
                '''))
                db.session.commit()
                print("Successfully created shift table")

            # Check if user_shift table exists
            result = db.session.execute(text("SHOW TABLES LIKE 'user_shift'"))
            if not result.fetchone():
                db.session.execute(text('''
                    CREATE TABLE user_shift (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        shift_id INT NOT NULL,
                        date DATE NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                        FOREIGN KEY (shift_id) REFERENCES shift(id) ON DELETE CASCADE
                    )
                '''))
                db.session.commit()
                print("Successfully created user_shift table")

        except Exception as e:
            db.session.rollback()
            print(f"Tables migration note: {str(e)[:100]}")

    @app.route('/dev/check-reload')
    @limiter.exempt
    def dev_check_reload():
        # Get the latest modified time of any file in templates/
        latest_mtime = 0
        template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
        try:
            for root, dirs, files in os.walk(template_dir):
                for file in files:
                    if file.endswith('.html'):
                        mtime = os.path.getmtime(os.path.join(root, file))
                        if mtime > latest_mtime:
                            latest_mtime = mtime
            return jsonify({'mtime': latest_mtime})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    app.run(debug=True, host='0.0.0.0', port=5002)
 