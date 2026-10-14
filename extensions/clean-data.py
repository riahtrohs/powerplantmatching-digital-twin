import os
import pandas as pd
import numpy as np


def get_config():
    return {}


def CUSTOM_CHINA(raw=False, update=False, config=None):
    config = get_config() if config is None else config

    # 读取原始数据文件（注意路径，确保 data/raw_china.csv 存在）
    fn = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw_china.csv")
    print(f"ℹ️ 自动解析文件路径：{fn}")

    if not os.path.exists(fn):
        raise FileNotFoundError(f"自定义中国电厂数据文件不存在: {fn}")

    # 读取CSV，跳过错误行
    df = pd.read_csv(fn, encoding="utf-8", encoding_errors="replace", on_bad_lines="skip")

    # ========== 1. 基础清洗与列名转换 ==========
    # 只保留中国的数据（根据原始表头 country 列筛选，通常是 'CHN' 或 'CN'）
    df = df[df['country'].isin(['CHN', 'CN', 'China'])]

    # 重命名核心列
    df = df.rename(columns={
        'name': 'Name',
        'capacity_mw': 'Capacity',
        'latitude': 'lat',
        'longitude': 'lon',
        'commissioning_year': 'DateIn',
        'gppd_idnr': 'id'
    })

    # ========== 2. 燃料类型映射 ==========
    # 把 WRI 的燃料类型映射到 powerplantmatching 的标准类型
    fuel_map = {
        'Coal': 'Hard Coal',
        'Gas': 'Natural Gas',
        'Hydro': 'Hydro',
        'Wind': 'Wind',
        'Solar': 'Solar',
        'Nuclear': 'Nuclear',
        'Oil': 'Oil',
        'Biomass': 'Biomass',
        'Waste': 'Waste',
        'Geothermal': 'Geothermal',
        'Storage': 'Storage'
    }
    df['Fueltype'] = df['primary_fuel'].map(fuel_map).fillna('Other')
    df['Technology'] = df['primary_fuel']  # 保留原始技术名称

    # ========== 3. 补齐 powerplantmatching 需要的 19 列 ==========
    df['Country'] = 'CN'  # 强制设为中国的 ISO 两位代码
    df['Set'] = 'PP'
    df['Efficiency'] = np.nan
    df['DateRetrofit'] = np.nan
    df['DateOut'] = np.nan
    df['Duration'] = np.nan
    df['Volume_Mm3'] = np.nan
    df['DamHeight_m'] = np.nan
    df['StorageCapacity_MWh'] = np.nan
    df['EIC'] = df['id']  # 用原始ID填补
    df['projectID'] = np.nan

    # ========== 4. 数据清洗（丢无效数据） ==========
    # 必须要有坐标和容量
    df = df.dropna(subset=['Capacity', 'lat', 'lon', 'Fueltype'])
    df = df[df['Capacity'] > 0]
    df = df[(df['lat'] != 0) & (df['lon'] != 0)]

    # 如果 Name 缺失，填个默认名
    df['Name'] = df['Name'].fillna('Unknown Plant')

    # ========== 5. 补充调度算法需要的边际成本 (marginal_cost) ==========
    cost_map = {
        'Solar': 0, 'Wind': 0, 'Hydro': 5, 'Nuclear': 10,
        'Natural Gas': 50, 'Hard Coal': 40, 'Lignite': 30, 'Oil': 80
    }
    df['marginal_cost'] = df['Fueltype'].map(cost_map).fillna(60)

    # ========== 6. 保留最终 20 列 (19列标准 + marginal_cost) ==========
    final_columns = [
        'id', 'Name', 'Fueltype', 'Technology', 'Set', 'Country',
        'Capacity', 'Efficiency', 'DateIn', 'DateRetrofit', 'DateOut',
        'lat', 'lon', 'Duration', 'Volume_Mm3', 'DamHeight_m',
        'StorageCapacity_MWh', 'EIC', 'projectID', 'marginal_cost'
    ]
    df = df[final_columns]

    # 保存清洗后的数据
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "custom_powerplants.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"✅ 清洗完成！已保存到：{out_path}，共 {len(df)} 个电厂。")
    return df


if __name__ == '__main__':
    cfg = get_config()
    df_clean = CUSTOM_CHINA(config=cfg)