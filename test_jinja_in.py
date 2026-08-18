import jinja2

class Obj:
    def __init__(self):
        self.child = None

try:
    t = jinja2.Template("{% if 'a' in obj.child.name %}yes{% endif %}")
    print(t.render(obj=Obj()))
except Exception as e:
    import traceback
    traceback.print_exc()
