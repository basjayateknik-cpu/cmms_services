from app import create_app
from models import db, AssetMeter, AssetMeterReading

app = create_app()
with app.app_context():
    # Delete child table first due to foreign key constraints in MySQL
    reading_count = AssetMeterReading.query.count()
    AssetMeterReading.query.delete()
    
    # Delete parent table
    meter_count = AssetMeter.query.count()
    AssetMeter.query.delete()
    
    db.session.commit()
    print(f"Deleted {reading_count} AssetMeterReadings and {meter_count} AssetMeters.")
