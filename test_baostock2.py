import baostock as bs
bs.login()
rs2 = bs.query_profit_data(code='sz.000001', year=2024, quarter=4)
rows2 = []
while (rs2.error_code == '0') and rs2.next():
    rows2.append(rs2.get_row_data())
print('profit fields:', rs2.fields)
if rows2:
    print('profit data:', rows2[0])

rs3 = bs.query_cash_flow_data(code='sz.000001', year=2024, quarter=4)
rows3 = []
while (rs3.error_code == '0') and rs3.next():
    rows3.append(rs3.get_row_data())
print('cash_flow fields:', rs3.fields)
if rows3:
    print('cash_flow data:', rows3[0])

rs4 = bs.query_growth_data(code='sz.000001', year=2024, quarter=4)
rows4 = []
while (rs4.error_code == '0') and rs4.next():
    rows4.append(rs4.get_row_data())
print('growth fields:', rs4.fields)
if rows4:
    print('growth data:', rows4[0])

rs5 = bs.query_operation_data(code='sz.000001', year=2024, quarter=4)
rows5 = []
while (rs5.error_code == '0') and rs5.next():
    rows5.append(rs5.get_row_data())
print('operation fields:', rs5.fields)
if rows5:
    print('operation data:', rows5[0])
bs.logout()
