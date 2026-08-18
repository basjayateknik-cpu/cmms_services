import jinja2
t = jinja2.Template("{{ x.name if x else '-' }}")
print(t.render(x=None))
