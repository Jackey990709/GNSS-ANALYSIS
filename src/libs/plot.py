import matplotlib
import numpy as np


matplotlib.use("Agg")  # 使用非GUI后端
import matplotlib.pyplot as plt


def plot_data(filepath: str, data: dict):
    # 创建画布 - 3行1列垂直排列
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), dpi=150)
    fig.suptitle("定位误差分析", fontsize=11, fontweight="bold")

    # 绘制水平误差曲线
    _plot_error_subplot(
        axes[0],
        data["axis"],
        data["horz_error"],
        "水平误差",
        "水平误差 (m)",
    )

    # 绘制垂直误差曲线
    _plot_error_subplot(
        axes[1],
        data["axis"],
        data["vert_error"],
        "高程误差",
        "高程误差 (m)",
    )

    # 绘制速度误差曲线
    _plot_error_subplot(
        axes[2],
        data["axis"],
        data["speed_error"],
        "速度误差",
        "速度误差 (m/s)",
    )

    # 调整布局
    plt.tight_layout()
    plt.subplots_adjust(top=0.94)

    # 保存图片
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()


def _plot_error_subplot(ax, axis, data, title: str, ylabel: str):
    values = np.array(data)

    # 绘制曲线
    ax.plot(axis, values, linewidth=0.5, alpha=0.8, color="gray")
    ax.scatter(axis, values, c="blue", s=1, alpha=0.6, zorder=5)

    ax.set_title(title, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.set_xlim(left=0)


def plot_bar(filepath: str, axis: list, values: list, title: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)

    # 绘制柱状图
    bars = ax.bar(axis, values, color="steelblue", edgecolor="black", alpha=0.8)

    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            height,
            ha="center",
            va="bottom",
            fontsize=10,
        )

    # 设置标题和标签
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=10)

    # 美化
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_ylim(0, max(values, default=1) * 1.15)  # 留出顶部空间

    # 保存图片
    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
