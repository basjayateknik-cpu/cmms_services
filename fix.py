with open('CMMS_mysql.sql', 'r', encoding='utf-8') as f:
    sql = f.read()
sql = sql.replace('CREATE DATABASE IF NOT EXISTS "cmms";', '')
sql = sql.replace('cmms.', '')
sql = sql.replace('AUTOINCREMENT', 'AUTO_INCREMENT')
with open('CMMS_mysql_fixed.sql', 'w', encoding='utf-8') as f:
    f.write(sql)
