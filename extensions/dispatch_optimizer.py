import pypsa
import pandas as pd
import numpy as np


def run_economic_dispatch(powerplants_df, load_series):
    """
    运行经济调度优化
    :param powerplants_df: 电厂数据，需包含 'name', 'Fueltype', 'Capacity', 'marginal_cost'
    :param load_series: 电力负荷曲线 (pandas Series)
    :return: 优化后的 PyPSA Network 对象
    """
    # 1. 初始化 PyPSA 网络
    n = pypsa.Network()
    # 设置时间快照（例如24小时）
    n.set_snapshots(load_series.index)

    # 2. 添加一个“母线”（Bus），代表电力系统的节点
    n.add("Bus", "electricity_bus", carrier="AC")

    # 3. 添加负荷（Load）
    n.add("Load", "total_load",
          bus="electricity_bus",
          p_set=load_series.values)

    # 4. 将电厂数据转换为 PyPSA 的 Generator 组件
    #    这里只选取有容量和成本数据的电厂
    valid_plants = powerplants_df.dropna(subset=['Capacity', 'marginal_cost'])

    for idx, plant in valid_plants.iterrows():
        n.add(
            "Generator",
            plant['Name'],  # 用电厂名称作为唯一ID
            bus="electricity_bus",
            p_nom=plant['Capacity'],  # 装机容量 (MW)
            marginal_cost=plant['marginal_cost'],  # 边际成本 (€/MWh)
            carrier=plant['Fueltype'],  # 燃料类型，用于分类
        )

    # 5. 运行优化！PyPSA 会自动选择成本最低的机组组合
    print("开始运行经济调度优化...")
    n.optimize(log_to_console=False)  # 关闭冗长的日志输出
    print("优化完成！")

    return n


if __name__ == '__main__':
    import powerplantmatching as ppm
    import numpy as np
    import pandas as pd

    print("1. 正在加载本地数据...")
    df = ppm.powerplants(update=False)

    # 为了测试速度，只取前50个最大电厂，防止算太久
    df = df.sort_values(by='Capacity', ascending=False).head(50).copy()

    # 【关键】PyPSA 需要每个电厂有“边际成本”(marginal_cost)
    # powerplantmatching 默认没有成本数据，我们按燃料类型写一个简单的成本表
    print("2. 正在给电厂添加假设的成本...")
    cost_map = {
        'Solar': 0, 'Wind': 0, 'Hydro': 5, 'Nuclear': 10,
        'Natural Gas': 50, 'Hard Coal': 40, 'Lignite': 30, 'Oil': 80
    }
    df['marginal_cost'] = df['Fueltype'].map(cost_map).fillna(60)  # 其他默认60

    # 3. 构造一个24小时的负荷曲线（模拟一天用电需求）
    print("3. 生成24小时负荷曲线...")
    load_series = pd.Series(
        np.linspace(2000, 8000, 24) + np.random.randint(-500, 500, 24),  # 假设负荷在2000-8000MW之间波动
        index=pd.date_range("2026-01-01", periods=24, freq="h")
    )

    # 4. 执行调度算法
    print("4. 开始执行调度优化...")
    try:
        net = run_economic_dispatch(df, load_series)
        print("5. ✅ 调度完成！总成本为:", round(net.objective, 2))
    except Exception as e:
        print("❌ 运行出错:", e)