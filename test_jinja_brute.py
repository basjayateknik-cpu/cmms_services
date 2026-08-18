import jinja2
import traceback

class Obj:
    def __init__(self):
        self.child = None

def test(tpl):
    try:
        jinja2.Template(tpl).render(obj=Obj())
    except Exception as e:
        if "has no attribute 'name'" in str(e):
            print(f"BINGO! {tpl!r} -> {type(e).__name__}: {e}")
        else:
            print(f"Other error for {tpl!r}: {e}")
    else:
        print(f"Success for {tpl!r}")

test('{{ obj.child.name }}')
test('{{ obj.child.name.something }}')
test('{% if obj.child.name %}yes{% endif %}')
test('{% for x in obj.child.name %}yes{% endfor %}')
test('{{ obj.child.name + "a" }}')
test('{{ obj.child.name|lower }}')
test('{% if "a" in obj.child.name %}yes{% endif %}')
test('{% if obj.child.name == "a" %}yes{% endif %}')
test('{{ {"a": obj.child.name} }}')
test('{% set x = obj.child.name %}{{ x }}')
test('{{ obj.child.name() }}')
test('{{ obj.child.name(1) }}')
test('{{ url_for(obj.child.name) }}')
test('{{ obj.child.name|length }}')
