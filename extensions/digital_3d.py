"""
发电厂数字孪生 - 3D 可视化扩展模块（交互筛选 + 中文 + 多选版）
作者：你的团队
"""

import os
import sys
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import powerplantmatching as ppm


# ============================================================
# 0. 中英文映射
# ============================================================
FUEL_CN = {
    'Hard Coal': '硬煤', 'Lignite': '褐煤', 'Natural Gas': '天然气',
    'Nuclear': '核电', 'Wind': '风电', 'Solar': '光伏', 'Hydro': '水电',
    'Oil': '燃油', 'Biomass': '生物质', 'Waste': '垃圾发电',
    'Other': '其他', 'Geothermal': '地热', 'Storage': '储能',
    'Wave and Tidal': '潮汐能', 'Mechanical Storage': '机械储能',
}
COUNTRY_CN = {
    'Germany': '德国', 'Poland': '波兰', 'France': '法国',
    'United Kingdom': '英国', 'Italy': '意大利', 'Spain': '西班牙',
    'Netherlands': '荷兰', 'Sweden': '瑞典', 'Norway': '挪威',
    'Denmark': '丹麦', 'Austria': '奥地利', 'Belgium': '比利时',
    'Czech Republic': '捷克', 'Portugal': '葡萄牙', 'Romania': '罗马尼亚',
    'Greece': '希腊', 'Finland': '芬兰', 'Switzerland': '瑞士',
    'Ireland': '爱尔兰', 'Hungary': '匈牙利', 'Bulgaria': '保加利亚',
    'Serbia': '塞尔维亚', 'Croatia': '克罗地亚', 'Slovakia': '斯洛伐克',
    'Slovenia': '斯洛文尼亚', 'Ukraine': '乌克兰',
}


def to_cn_fuel(x):   return FUEL_CN.get(x, x)
def to_cn_country(x): return COUNTRY_CN.get(x, x)


# ============================================================
# 1. 数据加载
# ============================================================
def load_all_data():
    print("⏳ 正在加载电厂数据...")
    df = ppm.powerplants(update=False)
    df = df.dropna(subset=['lat', 'lon']).copy()
    df = df.sort_values(by='Capacity', ascending=False).reset_index(drop=True)
    df['Fueltype_CN'] = df['Fueltype'].apply(to_cn_fuel)
    df['Country_CN'] = df['Country'].apply(to_cn_country)
    print(f"✅ 数据加载完成，共 {len(df)} 个电厂")
    return df


# ============================================================
# 2. 密度地形
# ============================================================
def compute_density_terrain(df, resolution=100, bandwidth=1.5):
    lat_min, lat_max = df['lat'].min(), df['lat'].max()
    lon_min, lon_max = df['lon'].min(), df['lon'].max()
    pad_lat = (lat_max - lat_min) * 0.05 + 1e-6
    pad_lon = (lon_max - lon_min) * 0.05 + 1e-6

    x = np.linspace(lon_min - pad_lon, lon_max + pad_lon, resolution)
    y = np.linspace(lat_min - pad_lat, lat_max + pad_lat, resolution)
    xx, yy = np.meshgrid(x, y)

    zz_density = np.zeros_like(xx)
    zz_capacity = np.zeros_like(xx)

    for lat, lon, cap in zip(df['lat'].values, df['lon'].values, df['Capacity'].values):
        dist2 = ((xx - lon) ** 2 + (yy - lat) ** 2) / (2 * bandwidth ** 2)
        w = np.exp(-dist2)
        zz_density += w
        zz_capacity += w * cap

    zz_density = zz_density / (zz_density.max() + 1e-9) * 100
    zz_capacity = zz_capacity / (zz_capacity.max() + 1e-9)
    return xx, yy, zz_density, zz_capacity


# ============================================================
# 3. 绘图
# ============================================================
def build_figure(df_filtered, top_n_countries=8, title_suffix=""):
    if df_filtered.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="⚠️ 当前筛选条件下没有数据，请调整筛选范围",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=20),
        )
        fig.update_layout(height=800, title="无数据")
        return fig

    xx, yy, zz_height, zz_capacity = compute_density_terrain(df_filtered)

    country_stats = (
        df_filtered.groupby(['Country_CN', 'Fueltype_CN'])['Capacity']
        .sum().reset_index()
    )
    top_countries = (
        df_filtered.groupby('Country_CN')['Capacity']
        .sum().sort_values(ascending=False)
        .head(top_n_countries).index.tolist()
    )
    country_stats = country_stats[country_stats['Country_CN'].isin(top_countries)]

    fig = make_subplots(
        rows=1, cols=2, column_widths=[0.7, 0.3],
        specs=[[{'type': 'surface'}, {'type': 'xy'}]],
        subplot_titles=(
            "资产空间分布：电厂密度地形图（高度=密度，颜色=装机容量）",
            f"能源结构：各国装机容量（Top {top_n_countries}）",
        ),
    )

    # 地形
    fig.add_trace(go.Surface(
        x=xx, y=yy, z=zz_height,
        surfacecolor=zz_capacity,
        colorscale='Viridis',
        colorbar=dict(title='装机容量<br>相对强度', x=0.42, len=0.7, thickness=15),
        opacity=0.85, showscale=True, name='空间密度地形',
        hovertemplate='经度: %{x:.2f}<br>纬度: %{y:.2f}<br>相对密度: %{z:.1f}<extra></extra>',
    ), row=1, col=1)

    # 电厂点
    cap_max = df_filtered['Capacity'].max()
    fig.add_trace(go.Scatter3d(
        x=df_filtered['lon'], y=df_filtered['lat'],
        z=zz_height.max() * 1.05 + df_filtered['Capacity'] / cap_max * 5,
        mode='markers',
        marker=dict(
            size=np.clip(df_filtered['Capacity'] / cap_max * 12, 2, 12),
            color=df_filtered['Capacity'],
            colorscale='Inferno', cmin=0, cmax=cap_max,
            line=dict(width=0.3, color='white'),
            opacity=0.9, showscale=False,
        ),
        text=df_filtered['Name'],
        customdata=np.stack([
            df_filtered['Country_CN'], df_filtered['Fueltype_CN'],
            df_filtered['Capacity'].round(1),
            df_filtered['lat'].round(3), df_filtered['lon'].round(3),
        ], axis=-1),
        hovertemplate=(
            '<b>%{text}</b><br>国家: %{customdata[0]}<br>'
            '燃料: %{customdata[1]}<br>装机容量: %{customdata[2]} MW<br>'
            '纬度: %{customdata[3]}<br>经度: %{customdata[4]}<extra></extra>'
        ),
        name='发电厂',
    ), row=1, col=1)

    # 能源结构堆叠柱
    qualitative_colors = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
        '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
        '#bcbd22', '#17becf', '#aec7e8', '#ffbb78',
    ]
    for i, fuel in enumerate(country_stats['Fueltype_CN'].unique()):
        sub = country_stats[country_stats['Fueltype_CN'] == fuel]
        fig.add_trace(go.Bar(
            x=sub['Country_CN'], y=sub['Capacity'], name=fuel,
            marker_color=qualitative_colors[i % len(qualitative_colors)],
            hovertemplate='%{x}<br>%{y:.0f} MW<extra></extra>',
        ), row=1, col=2)

    fig.update_layout(
        title=dict(text="🌍 发电厂数字孪生 · 交互筛选版" + title_suffix, font=dict(size=18)),
        height=800, barmode='stack',
        legend=dict(title='燃料类型', orientation='h', y=-0.15),
        scene=dict(
            xaxis_title='经度', yaxis_title='纬度',
            zaxis_title='空间密度（相对高度）',
            aspectmode='manual', aspectratio=dict(x=1, y=1, z=0.4),
            camera=dict(eye=dict(x=1.4, y=1.4, z=1.1)),
        ),
        margin=dict(l=0, r=0, t=100, b=60),
    )
    return fig


# ============================================================
# 4. 交互界面（多选 + 自动过滤稀有选项）
# ============================================================
# ============================================================
# 4. 交互界面（保留全部选项，标注数据量，空数据友好提示）
# ============================================================
def main():
    from dash import Dash, dcc, html, Input, Output

    df_all = load_all_data()

    # ---- 保留全部选项，但把每个选项的“电厂数量”标注在标签上 ----
    fuel_counts = df_all.groupby('Fueltype_CN').size().sort_values(ascending=False)
    country_counts = df_all.groupby('Country_CN').size().sort_values(ascending=False)

    # 燃料选项：全部保留，标签带数量
    fuel_options = [
        {'label': f"{fuel}（{cnt} 个）", 'value': fuel}
        for fuel, cnt in fuel_counts.items()
    ]

    # 国家选项：全部保留，按数量排序
    country_options = [
        {'label': f"{country}（{cnt} 个）", 'value': country}
        for country, cnt in country_counts.items()
    ]

    # 默认选中装机容量排名前 3 的燃料类型（避免初始空白，但用户可随意改）
    top_fuels = df_all.groupby('Fueltype_CN')['Capacity'].sum().sort_values(ascending=False).head(3).index.tolist()

    print(f"\n可用燃料类型共 {len(fuel_options)} 种")
    print(f"可用国家/地区共 {len(country_options)} 个")

    app = Dash(__name__)

    app.layout = html.Div([
        html.H2("🌍 发电厂数字孪生 · 交互筛选面板",
                style={'textAlign': 'center', 'marginBottom': '10px'}),

        html.Div([
            html.Label("燃料类型（可多选，清空=全部）："),
            dcc.Dropdown(
                id='fuel-dropdown',
                options=fuel_options,
                value=top_fuels,
                multi=True,
                placeholder="清空后显示全部燃料",
                style={'width': '340px', 'display': 'inline-block'}
            ),
            html.Label("国家/地区（可多选，清空=全部）：", style={'marginLeft': '20px'}),
            dcc.Dropdown(
                id='country-dropdown',
                options=country_options,
                value=[],
                multi=True,
                placeholder="清空后显示全部国家",
                style={'width': '340px', 'display': 'inline-block'}
            ),
            html.Label("最小容量 (MW)：", style={'marginLeft': '20px'}),
            dcc.Input(
                id='min-capacity', type='number', value=0, min=0, step=50,
                style={'width': '100px', 'display': 'inline-block'}
            ),
            html.Label("最大展示点数：", style={'marginLeft': '20px'}),
            dcc.Input(
                id='max-points', type='number', value=3000,
                min=100, max=20000, step=500,
                style={'width': '100px', 'display': 'inline-block'}
            ),
        ], style={
            'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center',
            'gap': '8px', 'padding': '12px', 'background': '#f5f5f5',
            'borderRadius': '8px', 'margin': '10px auto',
            'maxWidth': '1700px', 'flexWrap': 'wrap'
        }),

        dcc.Graph(id='main-graph', style={'height': '800px'}),
    ])

    @app.callback(
        Output('main-graph', 'figure'),
        [
            Input('fuel-dropdown', 'value'),
            Input('country-dropdown', 'value'),
            Input('min-capacity', 'value'),
            Input('max-points', 'value'),
        ]
    )
    def update_graph(fuels_sel, countries_sel, min_cap, max_pts):
        dff = df_all.copy()

        # 清空 = 全部（关键：不再自动过滤稀有类型）
        if fuels_sel:
            dff = dff[dff['Fueltype_CN'].isin(fuels_sel)]
        if countries_sel:
            dff = dff[dff['Country_CN'].isin(countries_sel)]
        if min_cap and min_cap > 0:
            dff = dff[dff['Capacity'] >= min_cap]

        dff = dff.sort_values(by='Capacity', ascending=False).head(int(max_pts))

        fuel_desc = "、".join(fuels_sel) if fuels_sel else "全部燃料"
        country_desc = "、".join(countries_sel) if countries_sel else "全部国家"
        title_suffix = f"（{fuel_desc} | {country_desc} | ≥{min_cap} MW | Top {int(max_pts)}）"

        # 额外信息：当前筛选条件下的电厂数量和总容量
        if not dff.empty:
            info = f"当前展示 {len(dff)} 个电厂，总容量 {dff['Capacity'].sum():.0f} MW"
        else:
            info = "当前筛选条件下无数据，请调整筛选范围"

        fig = build_figure(dff, top_n_countries=8, title_suffix=title_suffix)
        # 在图顶部加一行说明文字
        fig.add_annotation(
            text=info,
            xref="paper", yref="paper",
            x=0.5, y=1.05,
            showarrow=False,
            font=dict(size=13, color="#666"),
        )
        return fig

    print("\n✅ 服务已启动，浏览器打开 http://127.0.0.1:8050")
    print("   按 Ctrl+C 可停止服务。\n")
    app.run(debug=False, port=8050)


if __name__ == '__main__':
    main()


if __name__ == '__main__':
    main()