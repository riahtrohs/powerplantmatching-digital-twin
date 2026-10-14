import os
import pandas as pd


def get_config():
    return {}


def CUSTOM_CHINA(raw=False, update=False, config=None):
    config = get_config() if config is None else config

    fn = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw_china.csv")
    print(f"ℹ️ 自动解析文件路径：{fn}")

    if not os.path.exists(fn):
        raise FileNotFoundError(f"自定义中国电厂数据文件不存在: {fn}")

    df = pd.read_csv(
        fn,
        encoding="utf-8",
        encoding_errors="replace",
        on_bad_lines="skip"
    )

    # ========== 这里放你原本的清洗代码 ==========

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "custom_powerplants.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"✅ 清洗完成！已保存到：{out_path}，共 {len(df)} 个电厂。")
    return df


if __name__ == '__main__':
    cfg = get_config()
    df_clean = CUSTOM_CHINA(config=cfg)
    out_path = "./custom_powerplants.csv"
    df_clean.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"✅ 清洗完成！已保存为 {out_path}，共 {len(df_clean)} 个电厂。")
