import requests
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, AssetMeter, AssetMeterReading

logger = logging.getLogger(__name__)

def fetch_api_meter(app, meter_id):
    """Fetch data from an external API for a specific meter"""
    with app.app_context():
        meter = db.session.get(AssetMeter, meter_id)
        if not meter or not meter.api_url:
            return
            
        try:
            if meter.api_method == 'POST':
                response = requests.post(meter.api_url, timeout=10)
            else:
                response = requests.get(meter.api_url, timeout=10)
                
            response.raise_for_status()
            data = response.json()
            
            # Extract value using json key (e.g. "data.temperature")
            value = None
            if meter.api_json_key:
                keys = meter.api_json_key.split('.')
                current = data
                for k in keys:
                    if isinstance(current, dict) and k in current:
                        current = current[k]
                    else:
                        current = None
                        break
                value = current
            else:
                # If no key, assume the response itself is the value or has a 'value' key
                if isinstance(data, dict) and 'value' in data:
                    value = data['value']
                elif isinstance(data, (int, float, str)):
                    value = data
                    
            if value is not None:
                try:
                    numeric_val = float(value)
                    reading = AssetMeterReading(
                        meter_id=meter.id,
                        reading_value=numeric_val,
                        reading_date=datetime.utcnow()
                    )
                    db.session.add(reading)
                    db.session.commit()
                    logger.info(f"[API Poller] Logged reading {numeric_val} for meter {meter.name} from {meter.api_url}")
                except ValueError:
                    logger.warning(f"[API Poller] Invalid non-numeric value received for meter {meter.name}: {value}")
            else:
                logger.warning(f"[API Poller] Could not extract value for meter {meter.name} using key {meter.api_json_key}")
                
        except Exception as e:
            logger.error(f"[API Poller] Error fetching from {meter.api_url} for meter {meter.name}: {e}")


def init_api_poller(app):
    """Initialize APScheduler to poll all configured API meters"""
    scheduler = BackgroundScheduler()
    
    with app.app_context():
        # Get all meters that have an API URL configured
        api_meters = AssetMeter.query.filter(AssetMeter.api_url.isnot(None), AssetMeter.api_url != '').all()
        
        for meter in api_meters:
            interval = meter.api_interval if meter.api_interval and meter.api_interval > 0 else 5
            job_id = f"poll_meter_{meter.id}"
            
            scheduler.add_job(
                func=fetch_api_meter,
                trigger="interval",
                minutes=interval,
                args=[app, meter.id],
                id=job_id,
                replace_existing=True
            )
            logger.info(f"[API Poller] Scheduled polling for meter '{meter.name}' every {interval} minutes")
            
    scheduler.start()
    return scheduler
