"""
Load testing script untuk CMMS App
Install: pip install locust
Jalankan: locust --host=https://cmms.basjti.com
Buka browser: http://localhost:8089
Set: 50 users, spawn rate 5
"""
from locust import HttpUser, task, between

class CmmsUser(HttpUser):
    wait_time = between(1, 3)  # Simulasi user berpikir 1-3 detik antar request

    def on_start(self):
        """Login otomatis sebelum mulai test"""
        self.client.post("/auth/login", data={
            "nrp": "GANTI_NRP_ADMIN",       # <-- ganti
            "password": "GANTI_PASSWORD",    # <-- ganti
        }, allow_redirects=True)

    @task(5)
    def view_work_orders(self):
        self.client.get("/work-orders", name="WO List")

    @task(4)
    def view_dashboard(self):
        self.client.get("/dashboard", name="Dashboard")

    @task(3)
    def view_assets(self):
        self.client.get("/assets", name="Assets")

    @task(2)
    def create_wo_page(self):
        self.client.get("/work-orders/create", name="WO Create Form")

    @task(1)
    def view_supplies(self):
        self.client.get("/supplies", name="Supplies")
