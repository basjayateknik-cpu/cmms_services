import jinja2

class Obj:
    def __init__(self):
        self.user = None

t = jinja2.Template("{{ obj.user.name if obj.user else '-' }}")
print("Result:", t.render(obj=Obj()))
