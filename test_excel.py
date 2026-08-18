import pandas as pd
import xlsxwriter

output = 'test.xlsx'
writer = pd.ExcelWriter(output, engine='xlsxwriter')

df = pd.DataFrame(columns=['Project Code', 'Asset Name', 'Assignee Name'])
df.to_excel(writer, index=False, sheet_name='Import')

workbook = writer.book
worksheet = writer.sheets['Import']
ref_sheet = workbook.add_worksheet('Reference')

projects = ['PROJ-A', 'PROJ-B']
ref_sheet.write_column('A1', projects)
workbook.define_name('Projects', '=Reference!$A$1:$A$2')

ref_sheet.write_column('B1', ['Asset 1', 'Asset 2'])
workbook.define_name('PROJ_A', '=Reference!$B$1:$B$2')

ref_sheet.write_column('C1', ['Asset 3', 'Asset 4'])
workbook.define_name('PROJ_B', '=Reference!$C$1:$C$2')

worksheet.data_validation('A2:A1000', {'validate': 'list', 'source': '=Projects'})
worksheet.data_validation('B2:B1000', {'validate': 'list', 'source': '=INDIRECT(SUBSTITUTE($A2, "-", "_"))'})

writer.close()
