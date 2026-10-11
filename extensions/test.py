import powerplantmatching as ppm

print("=== 开始测试加载本地数据 ===")
# 这个函数会尝试读取项目里那个 38MB 的 powerplants.csv
df = ppm.powerplants()

print("=== 数据加载成功！ ===")
print("数据形状 (行, 列):", df.shape)
print("\n前5行数据预览:")
print(df.head())
print("\n所有列名:")
print(df.columns.tolist())