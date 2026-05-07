import baostock as bs
bs.login()
rs = bs.query_balance_data(code='sz.000001', year=2024, quarter=4)
rows = []
while (rs.error_code == '0') and rs.next():
    rows.append(rs.get_row_data())
print('fields:', rs.fields if hasattr(rs, 'fields') else 'N/A')
print('rows:', len(rows))
if rows:
    print(rows[0])
else:
    print('empty')
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
bs.logout()
