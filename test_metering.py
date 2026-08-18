import os
from flask import Flask, render_template, Blueprint
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
db = SQLAlchemy(app)
app.jinja_env.globals['csrf_token'] = lambda: 'dummy'
app.jinja_env.globals['url_for'] = lambda *args, **kwargs: 'dummy_url'

class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20))
    category_id = db.Column(db.Integer)
    subcategory_id = db.Column(db.Integer)
    site_id = db.Column(db.Integer)
    location_id = db.Column(db.Integer)
    project_code = db.Column(db.String(50))
    
    meters = db.relationship('AssetMeter', backref='asset', lazy='dynamic')
    
    @property
    def category(self): return None
    @property
    def subcategory(self): return None
    @property
    def site(self): return None
    @property
    def location(self): return None
    @property
    def custom_fields(self): return []

class AssetMeter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('asset.id'))
    name = db.Column(db.String(100))
    api_json_key = db.Column(db.String(100))
    api_url = db.Column(db.String(100))
    unit = db.Column(db.String(20))
    
    readings = db.relationship('AssetMeterReading', backref='meter', lazy='dynamic')

class AssetMeterReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meter_id = db.Column(db.Integer, db.ForeignKey('asset_meter.id'))
    reading_value = db.Column(db.Float)
    reading_date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer)
    is_anomaly = db.Column(db.Boolean)
    
    @property
    def user(self):
        class MockUser:
            name = None
        return MockUser()

class Checklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

with app.app_context():
    db.create_all()
    asset = Asset(name='Test Asset', status='Online')
    db.session.add(asset)
    db.session.flush()
    
    meter = AssetMeter(asset_id=asset.id, name=None)
    db.session.add(meter)
    db.session.flush()
    
    reading = AssetMeterReading(meter_id=meter.id, reading_value=1.0, reading_date=datetime.now())
    db.session.add(reading)
    db.session.commit()
    
    with app.test_request_context('/'):
        try:
            render_template('assets/tabs/metering.html', asset=asset, iot_api_cf=None, checklists=[], timedelta=timedelta)
            print("Rendered metering.html successfully")
        except Exception as e:
            import traceback
            traceback.print_exc()
