with open('work_orders.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('procedures_text = "\\n".join(procedures_list)', "procedures_text = chr(10).join(procedures_list)")
text = text.replace('checklist_text = "\\n".join(checklist_list)', "checklist_text = chr(10).join(checklist_list)")
text = text.replace('parts_text = "\\n".join(parts_list)', "parts_text = chr(10).join(parts_list)")

# Also fix the ones that got physically broken into two lines
text = text.replace('procedures_text = "\n".join(procedures_list)', "procedures_text = chr(10).join(procedures_list)")
text = text.replace('checklist_text = "\n".join(checklist_list)', "checklist_text = chr(10).join(checklist_list)")
text = text.replace('parts_text = "\n".join(parts_list)', "parts_text = chr(10).join(parts_list)")

with open('work_orders.py', 'w', encoding='utf-8') as f:
    f.write(text)
