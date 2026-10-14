import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.express import colors
from dash import Dash, dcc, html, Input, Output, State

# 路径处理，确保能导入同目录下的 dispatch_optimizer
sys.path.append(os.path.dirname(__file__))
from dispatch_optimizer import run_economic_dispatch

def load_data():
    """优先加载清洗后的中国数据，如果没有则报错提示"""
    china_csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "custom_powerplants.csv")

    if os.path.exists(china_csv_path):
        print(f"✅ 成功加载中国数据: {china_csv_path}")
        df = pd.read_csv(china_csv_path)
        if 'marginal_cost' not in df.columns:
            df['marginal_cost'] = 60
        # 【关键保命】限制在 50 个机组内，防止 PyPSA 计算爆炸
        df = df.sort_values(by='Capacity', ascending=False).head(50).copy()
        return df, "中国数据"
    else:
        raise FileNotFoundError(f"❌ 没有找到中国数据，请先运行 clean-data.py 生成 {china_csv_path}")


app = Dash(__name__)

app.layout = html.Div([
    html.H2("⚡ 发电厂经济调度优化展示", style={'textAlign': 'center'}),

    html.Div([
        html.Button('🚀 运行调度优化', id='run-dispatch-btn', n_clicks=0,
                    style={'fontSize': '18px', 'padding': '10px 20px', 'cursor': 'pointer',
                           'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none', 'borderRadius': '5px'}),
    ], style={'textAlign': 'center', 'margin': '20px'}),

    html.Div(id='status-msg', style={'textAlign': 'center', 'color': '#666', 'margin': '10px'}),
    html.Div(id='total-cost',
             style={'textAlign': 'center', 'fontSize': '24px', 'fontWeight': 'bold', 'color': '#d62728',
                    'margin': '10px'}),

    dcc.Graph(id='dispatch-result-graph', style={'height': '600px'})
])


@app.callback(
    [Output('dispatch-result-graph', 'figure'),
     Output('total-cost', 'children'),
     Output('status-msg', 'children')],
    [Input('run-dispatch-btn', 'n_clicks')]
)
def update_dispatch(n_clicks):
    if n_clicks == 0:
        return go.Figure(), "", "点击上方按钮开始计算经济调度..."

    try:
        df, data_source = load_data()
        status_msg = f"正在使用【{data_source}】进行计算..."

        # ================= 核心修复 1：动态负荷生成 =================
        # 根据当前读取到的电厂总容量，自动调整负荷，保证一定有可行解
        total_capacity = df['Capacity'].sum()
        if total_capacity > 0:
            # 让负荷在总容量的 30% 到 80% 之间波动（避免算不出来）
            load_series = pd.Series(
                np.linspace(total_capacity * 0.3, total_capacity * 0.8, 24) +
                np.random.uniform(-0.05, 0.05, 24) * total_capacity,
                index=pd.date_range("2026-01-01", periods=24, freq="h")
            )
        else:
            load_series = pd.Series(np.linspace(2000, 8000, 24),
                                    index=pd.date_range("2026-01-01", periods=24, freq="h"))

        # 调用优化函数
        res = run_economic_dispatch(df, load_series)

        # ================= 核心修复 2：健壮的图表构建 =================
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("24小时负荷与各燃料类型出力堆叠", "各燃料类型总出力占比")
        )

        # 左图：负荷曲线（黑色实线）
        fig.add_trace(go.Scatter(
            x=res['snapshots'], y=res['load_values'],
            mode='lines', name='系统负荷', line=dict(color='black', width=3)
        ), row=1, col=1)

        # 左图：各燃料类型出力（彩色堆叠）
        plotly_colors = colors.qualitative.Plotly
        for i, (carrier, gen_list) in enumerate(res['generation_by_carrier'].items()):
            fig.add_trace(go.Scatter(
                x=res['snapshots'], y=gen_list,
                mode='lines', stackgroup='one', name=carrier,
                line=dict(width=0.5, color=plotly_colors[i % len(plotly_colors)])
            ), row=1, col=1)

        # 右图：各燃料类型总出力柱状图
        total_by_carrier = {k: sum(v) for k, v in res['generation_by_carrier'].items()}
        fig.add_trace(go.Bar(
            x=list(total_by_carrier.keys()), y=list(total_by_carrier.values()),
            marker_color=plotly_colors[:len(total_by_carrier)], name='总出力'
        ), row=1, col=2)

        fig.update_layout(
            title_text="经济调度结果",
            height=600,
            template="plotly_white",
            legend_title="燃料类型"
        )

        return fig, f"✅ 优化完成！系统总成本: {res['objective']} 元", status_msg

    except Exception as e:
        import traceback
        traceback.print_exc()  # 打印详细错误到终端，方便排查
        return go.Figure(), "❌ 计算失败", f"报错信息: {str(e)}"


if __name__ == '__main__':
    print("✅ 启动调度展示面板，请访问 http://127.0.0.1:8051")
    app.run(debug=False, port=8051)