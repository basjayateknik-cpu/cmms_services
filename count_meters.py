from app import create_app
from models import AssetMeterReading, AssetMeter

app = create_app()
with app.app_context():
    print("Counting meters...")
    print(f"Meters: {AssetMeter.query.count()}")
    print("Counting readings...")
    print(f"Readings: {AssetMeterReading.query.count()}")
