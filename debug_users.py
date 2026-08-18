from app import create_app
from models import db, User, Site

app = create_app()

with app.app_context():
    print("All Sites:")
    sites = Site.query.all()
    for s in sites:
        print(f" - {s.name} (id={s.id})")
        
    print("\nAll Users:")
    users = User.query.all()
    for u in users:
        print(f" - {u.name} (site_id={u.site_id}, role={u.role})")
        
    print("\nSimulating site-based query (e.g., site_id=1 if exists):")
    if sites:
        test_site = sites[0]
        technicians = User.query.filter((User.site_id == test_site.id) | (User.site_id.is_(None))).all()
        print(f"Result for site {test_site.name}:")
        for t in technicians:
            print(f" -> {t.name} (role={t.role})")
    else:
        print("No sites available to test.")
