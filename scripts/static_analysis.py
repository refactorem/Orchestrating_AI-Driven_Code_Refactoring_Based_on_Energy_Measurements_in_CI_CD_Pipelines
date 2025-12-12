import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv("metrics.csv")

metrics = df['metric']
x = np.arange(len(metrics))
width = 0.35

colors = {'original': 'tab:blue', 'AI-generated refactored version': 'tab:orange'}

fig, ax = plt.subplots(figsize=(10,6))

ax.bar(x - width/2, df['original'], width, label='Original', color=colors['original'])
ax.bar(x + width/2, df['AI-generated refactored version'], width, label='AI-generated refactored version', color=colors['AI-generated refactored version'])

ax.set_xticks(x)
ax.set_xticklabels(metrics, rotation=45, ha='right')
ax.set_ylabel('Value')
ax.set_xlabel('Metric')
ax.set_title('Code metrics: Comparing original vs AI-generated refactored version')

for i in x:
    ax.text(i - width/2, df['original'][i] + 0.1, f"{df['original'][i]}", ha='center', va='bottom', fontsize=8)
    ax.text(i + width/2, df['AI-generated refactored version'][i] + 0.1, f"{df['AI-generated refactored version'][i]}", ha='center', va='bottom', fontsize=8)

ax.grid(axis='y', linestyle=':', linewidth=0.5)

fig.subplots_adjust(bottom=0.38)

fig.legend(
    loc='lower center',
    bbox_to_anchor=(0.5, 0.02),
    ncol=2,
    frameon=True,
    edgecolor='black',
    fontsize=9
)

plt.savefig("code_metrics_comparison_bar.pdf", bbox_inches='tight', format='pdf')
plt.show()
