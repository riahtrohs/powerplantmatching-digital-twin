import pypsa
import pandas as pd
import numpy as np


def run_economic_dispatch(powerplants_df, load_series):
    """
    运行经济调度优化，返回包含结果的字典
    """
    # 1. 初始化 PyPSA 网络
    n = pypsa.Network()
    n.set_snapshots(load_series.index)

    # 2. 添加母线
    n.add("Bus", "electricity_bus", carrier="AC")

    # 3. 添加负荷
    n.add("Load", "total_load",
          bus="electricity_bus",
          p_set=load_series.values)

    # 4. 添加发电机
    valid_plants = powerplants_df.dropna(subset=['Capacity', 'marginal_cost'])
    for idx, plant in valid_plants.iterrows():
        n.add(
            "Generator",
            str(plant['Name']),  # 确保 ID 是字符串，防止冲突
            bus="electricity_bus",
            p_nom=float(plant['Capacity']),
            marginal_cost=float(plant['marginal_cost']),
            carrier=str(plant['Fueltype']),
        )

    # 5. 运行优化
    print("开始运行经济调度优化...")
    n.optimize(log_to_console=False)
    print("优化完成！")

    # 6. 提取结果并打包成字典 (更稳健的写法)
    generation_df = n.generators_t.p.copy()

    # 用字典映射和 groupby 直接按燃料类型汇总出力，避免 join 报错
    carrier_map = n.generators['carrier'].to_dict()
    carrier_df = generation_df.T.groupby(carrier_map).sum().T

    results = {
        "objective": round(n.objective, 2) if n.objective else 0.0,
        "snapshots": [str(s) for s in n.snapshots],
        "load_values": load_series.tolist(),
        "generation_detail": generation_df.to_dict(orient="list"),
        "generation_by_carrier": carrier_df.to_dict(orient="list"),  # 这里是画图的关键数据
        "generators_capacity": n.generators['p_nom'].to_dict(),
        "generators_carrier": n.generators['carrier'].to_dict()
    }
    return results


if __name__ == '__main__':
    # 测试代码保持不变，用来验证后端逻辑
    import powerplantmatching as ppm

    print("1. 正在加载本地数据...")
    df = ppm.powerplants(update=False)
    df = df.sort_values(by='Capacity', ascending=False).head(50).copy()

    cost_map = {
        'Solar': 0, 'Wind': 0, 'Hydro': 5, 'Nuclear': 10,
        'Natural Gas': 50, 'Hard Coal': 40, 'Lignite': 30, 'Oil': 80
    }
    df['marginal_cost'] = df['Fueltype'].map(cost_map).fillna(60)

    load_series = pd.Series(
        np.linspace(2000, 8000, 24) + np.random.randint(-500, 500, 24),
        index=pd.date_range("2026-01-01", periods=24, freq="h")
    )

    print("2. 开始执行调度优化...")
    res = run_economic_dispatch(df, load_series)
    print(f"5. ✅ 调度完成！总成本为: {res['objective']}")
    print(f"   包含 {len(res['generation_by_carrier'])} 种燃料类型的调度数据。")